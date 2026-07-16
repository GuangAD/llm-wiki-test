from datetime import datetime
from pathlib import Path

from kb.core.atomic import atomic_write_text


def append_history(root: Path, event: str, title: str, details: list[str]) -> Path:
    path = root / "logs" / "history.md"
    existing = path.read_text(encoding="utf-8") if path.exists() else "# Knowledge History\n\n"
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [f"## [{timestamp}] {event} | {title}", ""]
    lines.extend(f"- {item}" for item in details)
    lines.append("")
    atomic_write_text(path, existing.rstrip() + "\n\n" + "\n".join(lines))
    return path
