import threading
import time
from collections import OrderedDict
from app.models import JobState, JobStatus, PageResult


class JobStore:
    """Thread-safe in-memory store for job state.

    BackgroundTasks runs in a threadpool while the event loop serves poll requests
    concurrently — the lock prevents torn reads/writes.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._jobs: OrderedDict[str, JobState] = OrderedDict()

    def create(self, job_id: str) -> JobState:
        state = JobState(
            job_id=job_id,
            status=JobStatus.QUEUED,
            message="Na fila...",
            created_at=time.time(),
        )
        with self._lock:
            self._jobs[job_id] = state
        return state

    def get(self, job_id: str) -> JobState | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **kwargs) -> None:
        with self._lock:
            state = self._jobs.get(job_id)
            if state is None:
                return
            updated = state.model_copy(update=kwargs)
            self._jobs[job_id] = updated

    def append_page(self, job_id: str, page: PageResult) -> None:
        with self._lock:
            state = self._jobs.get(job_id)
            if state is None:
                return
            new_pages = list(state.pages) + [page]
            self._jobs[job_id] = state.model_copy(update={"pages": new_pages})

    def purge_expired(self, ttl_seconds: int) -> int:
        cutoff = time.time() - ttl_seconds
        removed = 0
        with self._lock:
            expired = [jid for jid, s in self._jobs.items() if s.created_at < cutoff]
            for jid in expired:
                del self._jobs[jid]
                removed += 1
        return removed


job_store = JobStore()
