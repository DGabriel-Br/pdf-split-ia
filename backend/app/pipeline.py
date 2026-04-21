from app.config import Settings
from app.models import JobStatus, PageResult
from app.services.job_store import job_store
from app.services.pdf_extractor import extract_page_text, get_page_count
from app.services.ocr_service import ocr_page
from app.services.classifier import classify_page_sync
from app.services.pdf_builder import build_output_pdfs


def run_pipeline(job_id: str, pdf_path: str, settings: Settings) -> None:
    """Synchronous pipeline — runs in FastAPI BackgroundTasks threadpool."""
    try:
        job_store.update(job_id, status=JobStatus.EXTRACTING, message="Abrindo PDF...")
        total_pages = get_page_count(pdf_path)

        job_store.update(
            job_id,
            status=JobStatus.CLASSIFYING,
            message=f"Classificando 0 / {total_pages} páginas...",
        )

        page_results: list[PageResult] = []
        for i in range(total_pages):
            text, char_count = extract_page_text(pdf_path, i)
            used_ocr = False

            if char_count < settings.ocr_text_threshold:
                text = ocr_page(pdf_path, i, settings.ocr_confidence_threshold)
                used_ocr = True

            doc_type, confidence, raw, is_doc_start = classify_page_sync(text, i + 1, settings)

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
            job_store.append_page(job_id, result)

            progress = int(((i + 1) / total_pages) * 80)
            job_store.update(
                job_id,
                progress=progress,
                message=f"Classificando {i + 1} / {total_pages} páginas...",
            )

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
        )

    except Exception as exc:
        job_store.update(
            job_id,
            status=JobStatus.ERROR,
            error=str(exc),
            message=f"Erro no processamento: {exc}",
        )
        raise
