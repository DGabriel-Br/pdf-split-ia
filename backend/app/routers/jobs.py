import io
import os
import re
import zipfile
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.config import Settings, get_settings
from app.models import JobState, JobStatus
from app.services.job_store import job_store

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


@router.get("/jobs/{job_id}", response_model=JobState)
async def get_job_status(job_id: str) -> JobState:
    state = job_store.get(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    return state


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
