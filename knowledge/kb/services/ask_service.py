from pathlib import Path

import frontmatter

from kb.core.scoring import score_note


def ask(root: Path, question: str, max_notes: int = 5, min_score: int = 1) -> dict:
    hits = []
    for path in (root / "notes").glob("**/*.md"):
        post = frontmatter.loads(path.read_text(encoding="utf-8"))
        note = {
            "title": post.metadata.get("title", ""),
            "tags": post.metadata.get("tags", []),
            "summary": post.metadata.get("summary", ""),
            "body": post.content,
            "source_uri": post.metadata.get("source_uri", ""),
        }
        score = score_note(question, note)
        if score >= min_score:
            hits.append(
                {
                    "score": score,
                    "note_path": str(path.relative_to(root)),
                    "title": note["title"],
                    "summary": note["summary"],
                    "source_uri": note["source_uri"],
                }
            )
    hits.sort(key=lambda item: item["score"], reverse=True)
    return {
        "ok": True,
        "command": "kb ask",
        "status": "completed",
        "question": question,
        "notes": hits[:max_notes],
        "next_action": "none",
        "message": "Matched notes returned. Agent should compose answer with citations.",
    }
