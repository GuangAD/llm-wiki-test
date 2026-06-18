from pathlib import Path

import pytest

from kb.core.atomic import atomic_write_text
from kb.core.locks import IngestLockedError, ingest_lock


def test_atomic_write_text_writes_target(workspace: Path):
    target = workspace / "notes" / "note.md"

    atomic_write_text(target, "hello")

    assert target.read_text(encoding="utf-8") == "hello"
    assert not (workspace / "notes" / "note.md.tmp").exists()


def test_ingest_lock_rejects_existing_lock(workspace: Path):
    lock_path = workspace / "state" / "locks" / "ingest.lock"
    lock_path.parent.mkdir(parents=True)
    lock_path.write_text("locked", encoding="utf-8")

    with pytest.raises(IngestLockedError):
        with ingest_lock(workspace):
            pass
