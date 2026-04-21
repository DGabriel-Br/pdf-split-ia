import json
import time
import redis
from app.models import JobState, JobStatus, PageResult

_redis = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
_JOB_TTL = 3600  # seconds


def _key(job_id: str) -> str:
    return f"job:{job_id}"


def _text_key(job_id: str) -> str:
    return f"job:{job_id}:texts"


class JobStore:
    def create(self, job_id: str) -> JobState:
        state = JobState(
            job_id=job_id,
            status=JobStatus.QUEUED,
            message="Na fila...",
            created_at=time.time(),
        )
        _redis.setex(_key(job_id), _JOB_TTL, state.model_dump_json())
        return state

    def get(self, job_id: str) -> JobState | None:
        raw = _redis.get(_key(job_id))
        if raw is None:
            return None
        return JobState.model_validate_json(raw)

    def update(self, job_id: str, **kwargs) -> None:
        raw = _redis.get(_key(job_id))
        if raw is None:
            return
        state = JobState.model_validate_json(raw)
        updated = state.model_copy(update=kwargs)
        _redis.setex(_key(job_id), _JOB_TTL, updated.model_dump_json())

    def append_page(self, job_id: str, page: PageResult) -> None:
        raw = _redis.get(_key(job_id))
        if raw is None:
            return
        state = JobState.model_validate_json(raw)
        new_pages = list(state.pages) + [page]
        updated = state.model_copy(update={"pages": new_pages})
        _redis.setex(_key(job_id), _JOB_TTL, updated.model_dump_json())

    def store_page_text(self, job_id: str, page_number: int, text: str) -> None:
        _redis.hset(_text_key(job_id), str(page_number), text[:400])
        _redis.expire(_text_key(job_id), _JOB_TTL)

    def get_page_text(self, job_id: str, page_number: int) -> str:
        return _redis.hget(_text_key(job_id), str(page_number)) or ""

    def purge_expired(self, ttl_seconds: int) -> int:
        # Redis TTL handles expiration automatically
        return 0


job_store = JobStore()
