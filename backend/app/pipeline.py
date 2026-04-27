import logging
import re
from app.config import Settings
from app.models import DocumentType, JobStatus, PageResult
from app.services.job_store import job_store
from app.services.pdf_extractor import extract_all_page_texts, get_page_count
from app.services.ocr_service import ocr_page
from app.services.classifier import classify_page_sync
from app.services.pdf_builder import build_output_pdfs

log = logging.getLogger(__name__)

_INVOICE_REF_RE = re.compile(
    r"(?:invoice(?:\s+(?!no\b)\w+)?\s*no\.?|document\s+number)\s*[+:.]?\s*([A-Z$0-9/\-]{4,25})",
    re.IGNORECASE,
)

# Detects continuation pages: "page: 2", "seite 3", "invoice 2/3", "delivery 2/2".
# "page/seite" allow 0-5 non-digit chars before the number (e.g. "page: 2").
# "invoice/delivery/lieferschein" allow up to 25 non-digit chars (to skip "No." prefix).
# Second number limited to 1-2 digits to avoid matching long reference numbers.
_PAGE_CONT_RE = re.compile(
    r'\bpage\b[^0-9]{0,5}([2-9]|\d{2,3})\b'
    r'|\bseite\b[^0-9]{0,5}([2-9]|\d{2,3})\b'
    r'|\b(?:invoice|delivery|lieferschein)\b[^0-9]{0,25}([2-9]|[1-9]\d)\s*/\s*[1-9][0-9]?\b',
    re.IGNORECASE,
)

_OCR_NOISE = str.maketrans("$|", "SI")


def _normalize_ref(ref: str) -> str:
    """Normalize an invoice ref to resist common OCR substitutions ($ → S, | → I)."""
    return re.sub(r"[^A-Z0-9]", "", ref.upper().translate(_OCR_NOISE))


def _extract_invoice_ref(text: str) -> str | None:
    """Extract invoice number for same-document detection."""
    m = _INVOICE_REF_RE.search(text[:500])
    return m.group(1).strip() if m else None


def _fix_doc_boundaries(
    page_results: list[PageResult],
    page_texts: list[str],
) -> list[PageResult]:
    """Merge consecutive pages that belong to the same document.

    Handles three cases in priority order per page:
    1. INVOICE → INVOICE CONT — same invoice ref number, or explicit page marker.
    2. Any type → PACKING_LIST CONT — previous page is PACKING_LIST and current has page marker.
    3. OTHER → INVOICE CONT — previous page is INVOICE and current has page marker.
       Covers last pages of invoices that contain EU origin certificates or regulatory text.
    """
    fixed = list(page_results)
    for i in range(1, len(fixed)):
        cur  = fixed[i]
        prev = fixed[i - 1]

        if not cur.is_doc_start:
            continue

        text = page_texts[i]
        has_cont_marker = bool(_PAGE_CONT_RE.search(text))

        # 1. INVOICE consecutive merging (same type)
        if cur.doc_type == DocumentType.INVOICE and prev.doc_type == DocumentType.INVOICE:
            cur_ref  = _extract_invoice_ref(page_texts[i])
            prev_ref = _extract_invoice_ref(page_texts[i - 1])
            if cur_ref and prev_ref and _normalize_ref(cur_ref) == _normalize_ref(prev_ref):
                fixed[i] = cur.model_copy(update={"is_doc_start": False})
                log.debug("Pagina %d marcada como CONT (mesmo ref: %s)", cur.page_number, cur_ref)
                continue
            if has_cont_marker:
                fixed[i] = cur.model_copy(update={"is_doc_start": False})
                log.debug("Pagina %d marcada como CONT (indicador de pagina no texto)", cur.page_number)
                continue

        # 2. Cross-type → PACKING_LIST CONT (prev is PACKING_LIST, cur has continuation marker)
        if prev.doc_type == DocumentType.PACKING_LIST and has_cont_marker:
            fixed[i] = cur.model_copy(update={"is_doc_start": False, "doc_type": DocumentType.PACKING_LIST})
            log.debug(
                "Pagina %d reclassificada como PACKING_LIST CONT (prev=PACKING_LIST, marcador detectado)",
                cur.page_number,
            )
            continue

        # 3. Non-INVOICE → INVOICE CONT (prev=INVOICE, cur has cont marker)
        # Covers OTHER pages (EU certificates etc.) and pages misclassified as PACKING_LIST
        # that are actually continuations of an invoice.
        elif cur.doc_type != DocumentType.INVOICE and prev.doc_type == DocumentType.INVOICE and has_cont_marker:
            fixed[i] = cur.model_copy(update={"is_doc_start": False, "doc_type": DocumentType.INVOICE})
            log.debug(
                "Pagina %d reclassificada como INVOICE CONT (prev=INVOICE, cross-type, marcador detectado)",
                cur.page_number,
            )
            continue

    # Pass 2: post-process CONT pages.
    for i in range(1, len(fixed)):
        cur  = fixed[i]
        prev = fixed[i - 1]

        if cur.is_doc_start:
            continue

        # 2a. CONT after OTHER is suspicious — but only reset if the page itself has no
        # strong continuation marker (e.g. "Invoice 2/3"). If it has a marker, Ollama's
        # CONT label is likely correct despite the OTHER predecessor (which may itself be
        # misclassified due to garbled OCR).
        if prev.doc_type == DocumentType.OTHER:
            if not _PAGE_CONT_RE.search(page_texts[i]):
                log.debug("Pagina %d: CONT apos OTHER sem marcador, resetada para NEW", cur.page_number)
                fixed[i] = cur.model_copy(update={"is_doc_start": True})
            continue

        # 2b. Align type to predecessor when both are non-OTHER.
        # Handles Ollama correctly marking CONT position but misidentifying the type
        # (e.g. INVOICE CONT after PACKING_LIST → PACKING_LIST CONT).
        if cur.doc_type != prev.doc_type and cur.doc_type != DocumentType.OTHER:
            log.debug(
                "Pagina %d tipo alinhado com predecessor: %s -> %s",
                cur.page_number, cur.doc_type.value, prev.doc_type.value,
            )
            fixed[i] = cur.model_copy(update={"doc_type": prev.doc_type})

    return fixed


def run_pipeline(job_id: str, pdf_path: str, settings: Settings) -> None:
    """Synchronous pipeline — runs in Celery thread pool."""
    log.info("Pipeline iniciado job=%s pdf=%s", job_id, pdf_path)
    try:
        job_store.update(job_id, status=JobStatus.EXTRACTING, message="Abrindo PDF...")
        total_pages = get_page_count(pdf_path)
        log.info("job=%s total_pages=%d", job_id, total_pages)

        job_store.update(
            job_id,
            status=JobStatus.CLASSIFYING,
            message=f"Classificando 0 / {total_pages} páginas...",
        )

        all_page_texts = extract_all_page_texts(pdf_path)
        page_results: list[PageResult] = []
        page_texts: list[str] = []

        for i in range(total_pages):
            text, char_count = all_page_texts[i] if i < len(all_page_texts) else ("", 0)
            used_ocr = False

            if char_count < settings.ocr_text_threshold:
                text = ocr_page(pdf_path, i, settings.ocr_confidence_threshold)
                used_ocr = True

            doc_type, confidence, raw, is_doc_start = classify_page_sync(text, i + 1, settings)
            log.debug(
                "job=%s page=%d type=%s conf=%.2f ocr=%s label=%s",
                job_id, i + 1, doc_type.value, confidence, used_ocr, raw,
            )

            result = PageResult(
                page_number=i + 1,
                doc_type=doc_type,
                text_length=len(text),
                used_ocr=used_ocr,
                confidence=confidence,
                raw_label=raw[:200],
                is_doc_start=is_doc_start,
            )
            page_results.append(result)
            page_texts.append(text)
            job_store.append_page(job_id, result)

            progress = int(((i + 1) / total_pages) * 80)
            job_store.update(
                job_id,
                progress=progress,
                message=f"Classificando {i + 1} / {total_pages} páginas...",
            )

        # Correct boundaries: merge consecutive pages of the same document
        page_results = _fix_doc_boundaries(page_results, page_texts)

        # Persist the corrected page results (replaces the incrementally appended ones)
        job_store.update(job_id, pages=page_results)

        job_store.update(
            job_id,
            status=JobStatus.BUILDING,
            message="Gerando PDFs de saída...",
            progress=85,
        )

        output_paths = build_output_pdfs(
            pdf_path, page_results, settings.storage_output_dir, job_id
        )

        job_store.update(
            job_id,
            status=JobStatus.DONE,
            progress=100,
            message="Concluído.",
            output_files=output_paths,
            upload_file=pdf_path,
            page_texts_preview={str(i + 1): text[:300] for i, text in enumerate(page_texts)},
        )
        log.info("Pipeline concluido job=%s outputs=%s", job_id, list(output_paths.keys()))

    except Exception as exc:
        log.exception("Erro no pipeline job=%s: %s", job_id, exc)
        job_store.update(
            job_id,
            status=JobStatus.ERROR,
            error=str(exc),
            message=f"Erro no processamento: {exc}",
        )
        raise
