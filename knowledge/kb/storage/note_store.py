from pathlib import Path

import frontmatter

from kb.core.atomic import atomic_write_text


def write_note(root: Path, date_yyyymmdd: str, note_id: str, metadata: dict, body: str) -> Path:
    path = root / "notes" / date_yyyymmdd / f"{note_id}.md"
    post = frontmatter.Post(body, **metadata)
    atomic_write_text(path, frontmatter.dumps(post))
    return path


def iter_notes(root: Path) -> list[tuple[Path, frontmatter.Post]]:
    notes = []
    for path in sorted((root / "notes").glob("**/*.md")):
        notes.append((path, frontmatter.loads(path.read_text(encoding="utf-8"))))
    return notes


def write_note_post(path: Path, post: frontmatter.Post) -> Path:
    atomic_write_text(path, frontmatter.dumps(post))
    return path
