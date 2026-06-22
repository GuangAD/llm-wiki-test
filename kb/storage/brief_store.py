from pathlib import Path

from kb.core.atomic import atomic_write_text
from kb.core.models import BriefTopicsPayload, BriefWeeklyPayload


def write_topic_picks(root: Path, payload: BriefTopicsPayload, created_at: str) -> Path:
    date_key = payload.date.replace("-", "")
    path = root / "briefs" / f"topic-picks-{date_key}.md"
    lines = [
        "---",
        "type: brief_topics",
        f"date: {payload.date}",
        f"created_at: {created_at}",
        "---",
        "",
        "# 选题清单",
        "",
    ]
    for item in payload.topics:
        lines.extend(
            [
                f"## {item.title}",
                "",
                f"理由：{item.reason}",
                "",
                f"角度：{item.angle}",
                "",
                "来源：",
                *[f"- {note_id}" for note_id in item.source_note_ids],
                "",
            ]
        )
    atomic_write_text(path, "\n".join(lines))
    return path


def write_weekly(root: Path, payload: BriefWeeklyPayload, created_at: str) -> Path:
    path = root / "briefs" / f"weekly-{payload.week}.md"
    sections = [
        ("本周新增", payload.new_items),
        ("重点主题", payload.key_themes),
        ("未决问题", payload.open_questions),
        ("下一步", payload.next_actions),
    ]
    lines = [
        "---",
        "type: brief_weekly",
        f"week: {payload.week}",
        f"created_at: {created_at}",
        "---",
        "",
        "# 知识周报",
        "",
    ]
    for title, items in sections:
        lines.extend([f"## {title}", ""])
        lines.extend(f"- {item}" for item in items)
        lines.append("")
    atomic_write_text(path, "\n".join(lines))
    return path
