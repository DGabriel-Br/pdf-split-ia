from celery import Celery

celery_app = Celery(
    "pdf_split",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_prefetch_multiplier=1,  # one task per worker at a time
    task_acks_late=True,           # ack only after task completes
)
