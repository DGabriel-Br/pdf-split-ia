import logging
import re
from app.config import Settings
from app.models import DocumentType, JobStatus, PageResult
from app.services.job_store import job_store
from app.services.pdf_extractor import extract_page_text, get_page_count
from app.services.ocr_service import ocr_page
from app.services.classifier import classify_page_sync
from app.services.pdf_builder import build_output_pdfs

log = logging.getLogger(__name__)

_INVOICE_REF_RE = re.compile(
    r"invoice\s*no\.?\s*[:.]?\s*([A-Z0-9/\-]{4,25})",
    re.IGNORECASE,
)


def _extract_invoice_ref(text: str) -> str | None:
    """Extract invoice number for same-document detection."""
    m = _INVOICE_REF_RE.search(text[:500])
    return m.group(1).strip() if m else None


def _fix_doc_boundaries(
    page_results: list[PageResult],
    page_texts: list[str],
) -> list[PageResult]:
    """Merge consecutive INVOICE pages that share the same invoice reference number.

    Multi-page invoices (e.g. Robert Bosch 1/3, 2/3, 3/3) repeat the full header
    on every page, causing the classifier to mark each page as NEW. This pass checks
    consecutive INVOICE pages: if they share the same invoice reference number, the
    later pages are marked as CONT so the builder keeps them in one PDF.
    """
    fixed = list(page_results)
    for i in range(1, len(fixed)):
        cur  = fixed[i]
        prev = fixed[i - 1]

        if cur.doc_type != DocumentType.INVOICE or not cur.is_doc_start:
            continue
        if prev.doc_type != DocumentType.INVOICE:
            continue

        cur_ref  = _extract_invoice_ref(page_texts[i])
        prev_ref = _extract_invoice_ref(page_texts[i - 1])

        if cur_ref and prev_ref and cur_ref == prev_ref:
            fixed[i] = cur.model_copy(update={"is_doc_start": False})
            log.debug("Pagina %d marcada como CONT (mesmo ref: %s)", cur.page_number, cur_ref)

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

        page_results: list[PageResult] = []
        page_texts: list[str] = []

        for i in range(total_pages):
            text, char_count = extract_page_text(pdf_path, i)
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
