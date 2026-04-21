from app.worker import celery_app
from app.config import get_settings


@celery_app.task(bind=True, name="tasks.run_pipeline")
def run_pipeline_task(self, job_id: str, pdf_path: str) -> None:
    from app.pipeline import run_pipeline
    settings = get_settings()
    run_pipeline(job_id, pdf_path, settings)
