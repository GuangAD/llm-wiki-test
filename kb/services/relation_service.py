import re
from pathlib import Path

import frontmatter

from kb.core.topics import extract_topic_keys
from kb.storage.note_store import iter_notes, write_note_post

RELATION_THRESHOLD = 6


def _title_terms(title: str) -> set[str]:
    return {term.lower() for term in re.findall(r"[\w]+", title, flags=re.UNICODE)}


def _relation_score(current: frontmatter.Post, other: frontmatter.Post) -> int:
    current_tags = {str(tag).lower() for tag in current.metadata.get("tags", [])}
    other_tags = {str(tag).lower() for tag in other.metadata.get("tags", [])}
    tag_score = len(current_tags & other_tags) * 4

    current_terms = _title_terms(str(current.metadata.get("title", "")))
    other_terms = _title_terms(str(other.metadata.get("title", "")))
    title_score = len(current_terms & other_terms) * 2
    return tag_score + title_score


def _append_unique(values: list[str], new_values: list[str]) -> list[str]:
    merged = [str(value) for value in values]
    for value in new_values:
        if value not in merged:
            merged.append(value)
    return merged


def _topic_counts(notes: list[frontmatter.Post]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for post in notes:
        for key in post.metadata.get("topic_keys", []):
            counts[str(key)] = counts.get(str(key), 0) + 1
    return counts


def sync_relations(root: Path, current_note_id: str, related_topics: list[str]) -> dict:
    notes = iter_notes(root)
    note_by_id = {str(post.metadata.get("id", path.stem)): (path, post) for path, post in notes}
    if current_note_id not in note_by_id:
        raise FileNotFoundError(f"note not found: {current_note_id}")

    current_path, current = note_by_id[current_note_id]
    topic_keys = extract_topic_keys(related_topics)
    current.metadata["topic_keys"] = _append_unique(
        list(current.metadata.get("topic_keys", [])),
        topic_keys,
    )

    related_note_ids: list[str] = []
    changed_paths: set[Path] = {current_path}
    for other_id, (other_path, other) in note_by_id.items():
        if other_id == current_note_id:
            continue
        if _relation_score(current, other) < RELATION_THRESHOLD:
            continue
        related_note_ids.append(other_id)
        current.metadata["related_note_ids"] = _append_unique(
            list(current.metadata.get("related_note_ids", [])),
            [other_id],
        )
        other.metadata["related_note_ids"] = _append_unique(
            list(other.metadata.get("related_note_ids", [])),
            [current_note_id],
        )
        changed_paths.add(other_path)

    for path, post in note_by_id.values():
        if path in changed_paths:
            write_note_post(path, post)

    refreshed_notes = [post for _, post in iter_notes(root)]
    counts = _topic_counts(refreshed_notes)
    compilable_topic_keys = [key for key in topic_keys if counts.get(key, 0) >= 2]
    return {
        "related_note_ids": sorted(related_note_ids),
        "topic_keys": topic_keys,
        "compilable_topic_keys": sorted(compilable_topic_keys),
    }
