from pathlib import Path

from kb.core.atomic import atomic_write_text


def write_phase1_indexes(root: Path, recent: str, tags: str, sources: str) -> list[Path]:
    index_dir = root / "indexes"
    paths = [
        index_dir / "recent.md",
        index_dir / "tags.md",
        index_dir / "sources.md",
    ]
    for path, content in zip(paths, [recent, tags, sources], strict=True):
        atomic_write_text(path, content)
    return paths


def write_topics_index(root: Path, topics: list[tuple[str, str, str]]) -> Path:
    path = root / "indexes" / "topics.md"
    lines = ["# Topics", ""]
    for title, topic_key, topic_path in sorted(topics, key=lambda item: item[1]):
        lines.append(f"- [{title}](../{topic_path}): {topic_key}")
    atomic_write_text(path, "\n".join(lines) + "\n")
    return path


def write_insights_index(root: Path, insights: list[tuple[str, str]]) -> Path:
    path = root / "indexes" / "insights.md"
    lines = ["# Insights", ""]
    for title, insight_path in sorted(insights, key=lambda item: item[0]):
        lines.append(f"- [{title}](../{insight_path})")
    atomic_write_text(path, "\n".join(lines) + "\n")
    return path
