import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from app.config import Settings, get_settings
from app.services.job_store import job_store
from app.tasks import run_pipeline_task

router = APIRouter()


@router.post("/upload")
async def upload_pdf(
    file: UploadFile,
    settings: Settings = Depends(get_settings),
) -> dict:
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        if not (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Somente arquivos PDF são aceitos.")

    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo muito grande. Máximo: {settings.max_upload_size_mb} MB.",
        )

    job_id = uuid.uuid4().hex
    file_path = os.path.join(settings.storage_upload_dir, f"{job_id}.pdf")
    os.makedirs(settings.storage_upload_dir, exist_ok=True)

    with open(file_path, "wb") as f:
        f.write(content)

    job_store.create(job_id)
    run_pipeline_task.delay(job_id, file_path)

    return {"job_id": job_id}
