import io
import os
import re
import zipfile
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from app.models import JobState, JobStatus
from app.services.job_store import job_store

router = APIRouter()

_KEY_PATTERN = re.compile(r"^(INVOICE|PACKING_LIST)_(\d+)$")

# Chaves do formato antigo também aceitas
_LEGACY_KEYS = {"INVOICE", "PACKING_LIST"}


def _is_relevant_key(key: str) -> bool:
    return key in _LEGACY_KEYS or bool(_KEY_PATTERN.match(key))


@router.get("/jobs/{job_id}", response_model=JobState)
async def get_job_status(job_id: str) -> JobState:
    state = job_store.get(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    return state


@router.get("/jobs/{job_id}/download-all")
async def download_all(job_id: str) -> StreamingResponse:
    state = job_store.get(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    if state.status != JobStatus.DONE:
        raise HTTPException(status_code=409, detail="Processamento ainda não concluído.")

    files = {
        key: path
        for key, path in state.output_files.items()
        if _is_relevant_key(key) and os.path.exists(path)
    }

    if not files:
        raise HTTPException(status_code=404, detail="Nenhuma fatura ou packing list encontrada.")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for key, path in sorted(files.items()):
            arcname = key.lower() + ".pdf"
            zf.write(path, arcname)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="documentos_{job_id[:8]}.zip"'},
    )
