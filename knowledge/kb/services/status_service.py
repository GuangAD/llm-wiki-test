import re
from pathlib import Path


RECENT_RE = re.compile(r"^- \[(?P<title>.+?)\]\((?P<path>.+?)\)$")
TAG_RE = re.compile(r"^- (?P<tag>[^:]+): (?P<note_ids>.+)$")
SOURCE_RE = re.compile(r"^- (?P<source_uri>.+): (?P<note_id>[^:\s]+)$")


def _count_files(path: Path, pattern: str = "**/*.md") -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.glob(pattern) if item.is_file())


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _parse_recent(path: Path) -> list[dict]:
    recent = []
    for line in _read_lines(path):
        match = RECENT_RE.match(line.strip())
        if match:
            recent.append(
                {
                    "title": match.group("title"),
                    "path": match.group("path").removeprefix("../"),
                }
            )
    return recent


def _parse_tags(path: Path) -> list[dict]:
    tags = []
    for line in _read_lines(path):
        match = TAG_RE.match(line.strip())
        if match:
            note_ids = [item.strip() for item in match.group("note_ids").split(",")]
            tags.append(
                {
                    "tag": match.group("tag"),
                    "note_ids": [item for item in note_ids if item],
                }
            )
    return tags


def _parse_sources(path: Path) -> list[dict]:
    sources = []
    for line in _read_lines(path):
        match = SOURCE_RE.match(line.strip())
        if match:
            sources.append(
                {
                    "source_uri": match.group("source_uri"),
                    "note_id": match.group("note_id"),
                }
            )
    return sources


def status(root: Path) -> dict:
    index_paths = [
        root / "indexes" / "recent.md",
        root / "indexes" / "tags.md",
        root / "indexes" / "sources.md",
    ]

    return {
        "ok": True,
        "command": "kb status",
        "status": "completed",
        "counts": {
            "raw": _count_files(root / "raw"),
            "notes": _count_files(root / "notes"),
            "wiki": _count_files(root / "wiki"),
            "topics": _count_files(root / "wiki", "topic-*.md"),
            "insights": _count_files(root / "wiki", "insight-*.md"),
            "briefs": _count_files(root / "briefs"),
            "reports": _count_files(root / "reports"),
        },
        "recent_notes": _parse_recent(index_paths[0]),
        "tags": _parse_tags(index_paths[1]),
        "sources": _parse_sources(index_paths[2]),
        "index_paths": [str(path.relative_to(root)).replace("\\", "/") for path in index_paths],
        "next_action": "none",
        "message": "Knowledge base inventory returned from indexes and content directories.",
    }
