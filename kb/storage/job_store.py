import json
from pathlib import Path
from typing import Any

from kb.core.atomic import atomic_write_text


def job_path(root: Path, job_id: str) -> Path:
    return root / "state" / "jobs" / f"{job_id}.json"


def write_job(root: Path, job_id: str, data: dict[str, Any]) -> Path:
    path = job_path(root, job_id)
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2))
    return path


def read_job(root: Path, job_id: str) -> dict[str, Any]:
    return json.loads(job_path(root, job_id).read_text(encoding="utf-8"))
