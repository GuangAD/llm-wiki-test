from pathlib import Path

import frontmatter

from kb.core.atomic import atomic_write_text
from kb.core.models import TopicPayload


def write_topic(root: Path, payload: TopicPayload, created_at: str) -> Path:
    path = root / "wiki" / f"topic-{payload.topic_key}.md"
    body = "\n\n".join(
        [
            f"## 当前主题定义\n\n{payload.definition}",
            "## 已形成的主要结论\n\n"
            + "\n".join(f"- {item}" for item in payload.conclusions),
            "## 关键分歧/未决问题\n\n"
            + "\n".join(f"- {item}" for item in payload.disagreements),
            "## 可延伸方向\n\n" + "\n".join(f"- {item}" for item in payload.extensions),
            "## 来源笔记列表\n\n"
            + "\n".join(f"- {item}" for item in payload.source_note_ids),
        ]
    )
    post = frontmatter.Post(
        body,
        topic_key=payload.topic_key,
        title=payload.title,
        source_note_ids=payload.source_note_ids,
        updated_at=created_at,
        status="active",
    )
    atomic_write_text(path, frontmatter.dumps(post))
    return path


def iter_topics(root: Path) -> list[tuple[Path, frontmatter.Post]]:
    topics = []
    for path in sorted((root / "wiki").glob("topic-*.md")):
        topics.append((path, frontmatter.loads(path.read_text(encoding="utf-8"))))
    return topics
