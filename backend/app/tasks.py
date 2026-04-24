import logging
from app.worker import celery_app
from app.config import get_settings

log = logging.getLogger(__name__)


@celery_app.task(name="tasks.run_pipeline")
def run_pipeline_task(job_id: str, pdf_path: str) -> None:
    from app.pipeline import run_pipeline
    settings = get_settings()
    run_pipeline(job_id, pdf_path, settings)


@celery_app.task(name="tasks.weekly_classifier_review")
def weekly_classifier_review() -> None:
    from app.services.classifier_reviewer import analyze_and_propose
    log.info("Revisao semanal do classificador iniciada.")
    path = analyze_and_propose()
    if path:
        log.info("Revisao concluida. Proposta gerada em: %s", path)
    else:
        log.info("Revisao concluida. Sem novas correcoes para analisar.")
