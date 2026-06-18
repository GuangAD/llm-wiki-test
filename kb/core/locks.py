from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class IngestLockedError(RuntimeError):
    pass


@contextmanager
def ingest_lock(root: Path) -> Iterator[None]:
    lock_path = root / "state" / "locks" / "ingest.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        raise IngestLockedError("Another ingest job is running.")
    lock_path.write_text("locked", encoding="utf-8")
    try:
        yield
    finally:
        if lock_path.exists():
            lock_path.unlink()
