import logging
import os
import shutil
import time
import redis
from app.config import get_settings
from app.models import JobState, JobStatus, PageResult

log = logging.getLogger(__name__)

_pool: redis.ConnectionPool | None = None


def _get_redis() -> redis.Redis:
    global _pool
    if _pool is None:
        s = get_settings()
        _pool = redis.ConnectionPool(
            host=s.redis_host,
            port=s.redis_port,
            db=s.redis_db,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            max_connections=10,
        )
    return redis.Redis(connection_pool=_pool)


def _key(job_id: str) -> str:
    return f"job:{job_id}"


def _ttl() -> int:
    return get_settings().job_ttl_seconds


class JobStore:
    def create(self, job_id: str) -> JobState:
        state = JobState(
            job_id=job_id,
            status=JobStatus.QUEUED,
            message="Na fila...",
            created_at=time.time(),
        )
        _get_redis().setex(_key(job_id), _ttl(), state.model_dump_json())
        return state

    def get(self, job_id: str) -> JobState | None:
        raw = _get_redis().get(_key(job_id))
        if raw is None:
            return None
        return JobState.model_validate_json(raw)

    def update(self, job_id: str, **kwargs) -> None:
        r = _get_redis()
        raw = r.get(_key(job_id))
        if raw is None:
            log.warning("Update para job inexistente: %s", job_id)
            return
        state = JobState.model_validate_json(raw)
        updated = state.model_copy(update=kwargs)
        r.setex(_key(job_id), _ttl(), updated.model_dump_json())

    def append_page(self, job_id: str, page: PageResult) -> None:
        r = _get_redis()
        raw = r.get(_key(job_id))
        if raw is None:
            log.warning("append_page para job inexistente: %s", job_id)
            return
        state = JobState.model_validate_json(raw)
        new_pages = list(state.pages) + [page]
        updated = state.model_copy(update={"pages": new_pages})
        r.setex(_key(job_id), _ttl(), updated.model_dump_json())

    def delete_upload_file(self, job_id: str) -> None:
        """Remove the uploaded PDF after pipeline processing is complete."""
        upload_dir = get_settings().storage_upload_dir
        path = os.path.join(upload_dir, f"{job_id}.pdf")
        try:
            if os.path.exists(path):
                os.remove(path)
                log.info("Upload removido: %s", path)
        except OSError as exc:
            log.warning("Falha ao remover upload %s: %s", path, exc)

    def cleanup_old_files(self, upload_dir: str, output_dir: str, max_age_seconds: int) -> int:
        """Delete files and output directories older than max_age_seconds. Called on startup."""
        now = time.time()
        removed = 0
        for directory in (upload_dir, output_dir):
            if not os.path.isdir(directory):
                continue
            for entry in os.scandir(directory):
                try:
                    age = now - entry.stat().st_mtime
                    if age > max_age_seconds:
                        if entry.is_file():
                            os.remove(entry.path)
                        elif entry.is_dir():
                            shutil.rmtree(entry.path)
                        removed += 1
                except OSError as exc:
                    log.warning("Falha ao limpar %s: %s", entry.path, exc)
        return removed


job_store = JobStore()
