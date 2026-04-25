import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from app.config import Settings, get_settings
from app.services.job_store import job_store
from app.tasks import run_pipeline_task

router = APIRouter()

_CHUNK_SIZE = 64 * 1024  # 64 KB


@router.post("/upload", status_code=202)
async def upload_pdf(
    file: UploadFile,
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        if not (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Somente arquivos PDF são aceitos.")

    # Stream the upload in chunks so large files are rejected early, not after full buffering
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = await file.read(_CHUNK_SIZE)
        if not chunk:
            break
        size += len(chunk)
        if size > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Arquivo muito grande. Máximo: {settings.max_upload_size_mb} MB.",
            )
        chunks.append(chunk)

    content = b"".join(chunks)
    if not content[:4].startswith(b'%PDF'):
        raise HTTPException(status_code=400, detail="O arquivo não é um PDF válido.")

    job_id = uuid.uuid4().hex
    file_path = os.path.join(settings.storage_upload_dir, f"{job_id}.pdf")

    with open(file_path, "wb") as f:
        f.write(content)

    job_store.create(job_id)
    run_pipeline_task.delay(job_id, file_path)

    return JSONResponse({"job_id": job_id}, status_code=202)
