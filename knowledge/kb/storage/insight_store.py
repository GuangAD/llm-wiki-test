from hashlib import sha256
from pathlib import Path

import frontmatter

from kb.core.atomic import atomic_write_text
from kb.core.models import AnswerPayload


def write_insight(root: Path, payload: AnswerPayload, created_at: str) -> Path:
    date_key = created_at[:10].replace("-", "")
    question_hash = sha256(payload.question.encode("utf-8")).hexdigest()[:8]
    path = root / "wiki" / f"insight-{date_key}-{question_hash}.md"
    source_paths = [citation.path for citation in payload.citations]
    source_uris = [citation.source_uri for citation in payload.citations if citation.source_uri]
    sources = ["## 来源", ""]
    for citation in payload.citations:
        suffix = f" — {citation.source_uri}" if citation.source_uri else ""
        sources.append(f"- `{citation.path}`{suffix}")
    post = frontmatter.Post(
        payload.answer_markdown.rstrip() + "\n\n" + "\n".join(sources),
        type="insight",
        title=payload.title,
        question=payload.question,
        topic_keys=payload.topic_keys,
        source_paths=source_paths,
        source_uris=source_uris,
        created_at=created_at,
        status="active",
    )
    atomic_write_text(path, frontmatter.dumps(post))
    return path


def iter_insights(root: Path) -> list[tuple[Path, frontmatter.Post]]:
    insights = []
    for path in sorted((root / "wiki").glob("insight-*.md")):
        insights.append((path, frontmatter.loads(path.read_text(encoding="utf-8"))))
    return insights
