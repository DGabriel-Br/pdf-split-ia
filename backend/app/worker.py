from celery import Celery
from celery.schedules import crontab
from app.config import get_settings

_s = get_settings()
_broker = f"redis://{_s.redis_host}:{_s.redis_port}/{_s.redis_db}"

celery_app = Celery("pdf_split", broker=_broker, backend=_broker, include=["app.tasks"])

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    timezone="America/Sao_Paulo",
    enable_utc=True,
    beat_schedule={
        "weekly-classifier-review": {
            "task": "tasks.weekly_classifier_review",
            "schedule": crontab(hour=8, minute=0, day_of_week="monday"),
        },
    },
)
