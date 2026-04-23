import io
import logging
import os
import re
import shutil
import zipfile
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.config import Settings, get_settings
from app.models import DocumentType, JobState, JobStatus, PageResult
from app.services.job_store import job_store
from app.services.pdf_builder import build_output_pdfs
from app.services.correction_store import save_corrections

log = logging.getLogger(__name__)

router = APIRouter()

_KEY_PATTERN = re.compile(r"^(INVOICE|PACKING_LIST)_(\d+)$")
_LEGACY_KEYS = {"INVOICE", "PACKING_LIST"}


def _is_relevant_key(key: str) -> bool:
    return key in _LEGACY_KEYS or bool(_KEY_PATTERN.match(key))


def _safe_output_paths(
    output_files: dict[str, str],
    output_dir: str,
) -> dict[str, str]:
    """Return only paths that exist and reside inside output_dir (path traversal guard)."""
    base = os.path.realpath(output_dir)
    safe: dict[str, str] = {}
    for key, path in output_files.items():
        if not _is_relevant_key(key):
            continue
        real = os.path.realpath(path)
        if not real.startswith(base + os.sep):
            continue
        if os.path.isfile(real):
            safe[key] = real
    return safe


class ReclassifyRequest(BaseModel):
    page_types: dict[int, DocumentType]


@router.get("/jobs/{job_id}", response_model=JobState)
async def get_job_status(job_id: str) -> JobState:
    state = job_store.get(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    return state


@router.post("/jobs/{job_id}/reclassify", response_model=JobState)
async def reclassify(
    job_id: str,
    body: ReclassifyRequest,
    settings: Settings = Depends(get_settings),
) -> JobState:
    state = job_store.get(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    if state.status != JobStatus.DONE:
        raise HTTPException(status_code=409, detail="Processamento ainda não concluído.")
    if not state.upload_file or not os.path.isfile(state.upload_file):
        raise HTTPException(
            status_code=410,
            detail="Arquivo original não disponível. O prazo de reclassificação expirou.",
        )

    # Apply corrections; pages whose type changed get is_doc_start=True
    original_types = {p.page_number: p.doc_type for p in state.pages}
    updated_pages: list[PageResult] = []
    for page in sorted(state.pages, key=lambda p: p.page_number):
        new_type = body.page_types.get(page.page_number, page.doc_type)
        type_changed = new_type != original_types[page.page_number]
        updated_pages.append(
            page.model_copy(update={
                "doc_type": new_type,
                "is_doc_start": True if type_changed else page.is_doc_start,
            })
        )

    # Persist corrections for future pre-filter review
    changed = [
        {
            "page_number": p.page_number,
            "original_type": original_types[p.page_number].value,
            "corrected_type": p.doc_type.value,
            "raw_label": p.raw_label,
            "confidence": round(p.confidence, 3),
            "text_preview": state.page_texts_preview.get(str(p.page_number), ""),
        }
        for p in updated_pages
        if p.doc_type != original_types[p.page_number]
    ]
    save_corrections(job_id, changed, upload_file=state.upload_file)

    # Clear old output directory so stale files don't linger
    job_out_dir = os.path.join(settings.storage_output_dir, job_id)
    if os.path.isdir(job_out_dir):
        shutil.rmtree(job_out_dir)

    output_paths = build_output_pdfs(
        state.upload_file, updated_pages, settings.storage_output_dir, job_id
    )
    log.info("Reclassificacao concluida job=%s outputs=%s", job_id, list(output_paths.keys()))

    job_store.update(job_id, pages=updated_pages, output_files=output_paths)
    return job_store.get(job_id)


@router.get("/jobs/{job_id}/download-all")
async def download_all(
    job_id: str,
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    state = job_store.get(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    if state.status != JobStatus.DONE:
        raise HTTPException(status_code=409, detail="Processamento ainda não concluído.")

    files = _safe_output_paths(state.output_files, settings.storage_output_dir)
    if not files:
        raise HTTPException(status_code=404, detail="Nenhuma fatura ou packing list encontrada.")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for key, path in sorted(files.items()):
            zf.write(path, key.lower() + ".pdf")
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="documentos_{job_id[:8]}.zip"'},
    )
