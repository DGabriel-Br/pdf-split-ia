import os
from PyPDF2 import PdfReader, PdfWriter
from app.models import DocumentType, PageResult

_SPLIT_TYPES = {DocumentType.INVOICE, DocumentType.PACKING_LIST}


def _consecutive_groups(page_results: list[PageResult]) -> list[tuple[DocumentType, list[PageResult]]]:
    """Return (doc_type, pages) groups, splitting also when a new document starts within the same type."""
    groups: list[tuple[DocumentType, list[PageResult]]] = []
    current_type: DocumentType | None = None
    current_pages: list[PageResult] = []

    for page in page_results:
        new_doc = page.is_doc_start and bool(current_pages)
        if page.doc_type != current_type or new_doc:
            if current_pages:
                groups.append((current_type, current_pages))
            current_type = page.doc_type
            current_pages = [page]
        else:
            current_pages.append(page)

    if current_pages:
        groups.append((current_type, current_pages))

    return groups


def build_output_pdfs(
    source_pdf_path: str,
    page_results: list[PageResult],
    output_dir: str,
    job_id: str,
) -> dict[str, str]:
    """Split pages into one PDF per consecutive document block.

    Only INVOICE and PACKING_LIST blocks are written.
    Keys follow the pattern INVOICE_1, INVOICE_2, PACKING_LIST_1, etc.
    Returns mapping of key -> absolute file path.
    """
    reader = PdfReader(source_pdf_path)
    job_out_dir = os.path.join(output_dir, job_id)
    os.makedirs(job_out_dir, exist_ok=True)

    counters = {DocumentType.INVOICE: 0, DocumentType.PACKING_LIST: 0}
    output_paths: dict[str, str] = {}

    for doc_type, pages in _consecutive_groups(page_results):
        if doc_type not in _SPLIT_TYPES:
            continue

        counters[doc_type] += 1
        n = counters[doc_type]

        if doc_type == DocumentType.INVOICE:
            key = f"INVOICE_{n}"
            filename = f"invoice_{n}.pdf"
        else:
            key = f"PACKING_LIST_{n}"
            filename = f"packing_list_{n}.pdf"

        writer = PdfWriter()
        for page in pages:
            writer.add_page(reader.pages[page.page_number - 1])

        path = os.path.join(job_out_dir, filename)
        with open(path, "wb") as f:
            writer.write(f)
        output_paths[key] = os.path.abspath(path)

    return output_paths
