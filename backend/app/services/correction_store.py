import json
import logging
import os
from datetime import datetime, timezone
from app.config import get_settings

log = logging.getLogger(__name__)


def save_corrections(job_id: str, corrections: list[dict]) -> None:
    """Append corrected pages to the corrections log for future pre-filter improvements."""
    if not corrections:
        return
    path = get_settings().corrections_file
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with open(path, "a", encoding="utf-8") as f:
        for c in corrections:
            f.write(json.dumps({"timestamp": ts, "job_id": job_id, **c}, ensure_ascii=False) + "\n")
    log.info("Salvas %d correcao(oes) job=%s", len(corrections), job_id)


def load_all() -> list[dict]:
    path = get_settings().corrections_file
    if not os.path.isfile(path):
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records
