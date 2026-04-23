import json
import logging
import os
from datetime import datetime, timezone
from PyPDF2 import PdfReader, PdfWriter
from app.config import get_settings

log = logging.getLogger(__name__)


def _extract_page_pdf(source_pdf: str, page_number: int, dest_path: str) -> bool:
    """Extract a single page (1-based) from source_pdf and save it to dest_path."""
    try:
        reader = PdfReader(source_pdf)
        idx = page_number - 1
        if idx < 0 or idx >= len(reader.pages):
            return False
        writer = PdfWriter()
        writer.add_page(reader.pages[idx])
        with open(dest_path, "wb") as f:
            writer.write(f)
        return True
    except Exception as exc:
        log.warning("Falha ao extrair pagina %d para corrections: %s", page_number, exc)
        return False


def save_corrections(
    job_id: str,
    corrections: list[dict],
    upload_file: str | None = None,
) -> None:
    """Persist corrected pages to corrections.jsonl and save individual PDF pages for review."""
    if not corrections:
        return
    s = get_settings()
    os.makedirs(os.path.dirname(os.path.abspath(s.corrections_file)), exist_ok=True)
    os.makedirs(s.corrections_dir, exist_ok=True)

    ts = datetime.now(timezone.utc).isoformat()
    with open(s.corrections_file, "a", encoding="utf-8") as f:
        for c in corrections:
            pdf_page_path = None
            if upload_file and os.path.isfile(upload_file):
                dest = os.path.join(s.corrections_dir, f"{job_id}_p{c['page_number']}.pdf")
                if _extract_page_pdf(upload_file, c["page_number"], dest):
                    pdf_page_path = os.path.abspath(dest)

            record = {"timestamp": ts, "job_id": job_id, "pdf_page": pdf_page_path, **c}
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    log.info("Salvas %d correcao(oes) job=%s", len(corrections), job_id)


def _last_review_path() -> str:
    return get_settings().corrections_file.replace(".jsonl", "_last_review.txt")


def load_unreviewed() -> list[dict]:
    """Return corrections that haven't been processed in a previous weekly review."""
    all_records = load_all()
    path = _last_review_path()
    if not os.path.isfile(path):
        return all_records
    with open(path) as f:
        last_ts = f.read().strip()
    return [r for r in all_records if r["timestamp"] > last_ts]


def save_last_review_time(ts: str) -> None:
    with open(_last_review_path(), "w") as f:
        f.write(ts)


def load_all() -> list[dict]:
    path = get_settings().corrections_file
    if not os.path.isfile(path):
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records
