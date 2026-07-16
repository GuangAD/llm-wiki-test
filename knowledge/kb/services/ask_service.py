from datetime import datetime
from pathlib import Path

import frontmatter
from pydantic import ValidationError

from kb.core.errors import error_response
from kb.core.ids import build_job_id, build_request_id
from kb.core.models import AnswerPayload
from kb.core.scoring import score_note, score_wiki
from kb.storage.generation_store import read_generation_result, result_path, write_generation_request
from kb.storage.index_store import write_insights_index
from kb.storage.insight_store import iter_insights, write_insight
from kb.storage.job_store import read_job, write_job
from kb.storage.log_store import append_history
from kb.storage.note_store import iter_notes
from kb.storage.topic_store import iter_topics


def _now() -> datetime:
    return datetime.now().astimezone()


def _note_by_id(root: Path) -> dict[str, Path]:
    return {
        str(post.metadata.get("id", path.stem)): path
        for path, post in iter_notes(root)
    }


def _wiki_hits(root: Path, question: str) -> list[tuple[int, Path, frontmatter.Post]]:
    hits = []
    for path, post in [*iter_topics(root), *iter_insights(root)]:
        score = score_wiki(
            question,
            {
                "title": str(post.metadata.get("title", path.stem)),
                "topic_key": str(post.metadata.get("topic_key", "")),
                "body": post.content,
            },
        )
        if score:
            hits.append((score, path, post))
    return sorted(hits, key=lambda item: item[0], reverse=True)[:3]


def _note_hits(root: Path, question: str) -> list[tuple[int, Path]]:
    hits = []
    for path, post in iter_notes(root):
        score = score_note(
            question,
            {
                "title": post.metadata.get("title", ""),
                "tags": post.metadata.get("tags", []),
                "summary": post.metadata.get("summary", ""),
                "body": post.content,
                "source_uri": post.metadata.get("source_uri", ""),
            },
        )
        if score:
            hits.append((score, path))
    return sorted(hits, key=lambda item: item[0], reverse=True)[:5]


def select_source_paths(root: Path, question: str) -> list[str]:
    wiki_hits = _wiki_hits(root, question)
    paths: list[Path] = [path for _, path, _ in wiki_hits]
    if wiki_hits:
        notes = _note_by_id(root)
        for _, _, post in wiki_hits:
            note_ids = [
                *post.metadata.get("source_note_ids", []),
                *post.metadata.get("source_paths", []),
            ]
            for value in note_ids:
                value_str = str(value)
                path = notes.get(value_str)
                candidate = root / value_str
                if path is None and value_str.startswith("notes/") and candidate.exists():
                    path = candidate
                if path and path not in paths:
                    paths.append(path)
    else:
        paths.extend(path for _, path in _note_hits(root, question))
    return [path.relative_to(root).as_posix() for path in paths]


def request_answer(root: Path, question: str, save: bool = False) -> dict:
    source_paths = select_source_paths(root, question)
    if not source_paths:
        return error_response(
            command="kb ask",
            status="permanent_failed",
            error_code="NO_MATCH",
            error_message="No matching wiki pages or notes were found.",
            retryable=False,
            next_action="none",
        )
    now = _now()
    stamp = now.strftime("%Y%m%d%H%M%S")
    source_key = f"answer:{save}:{question}:{now.isoformat()}"
    job_id = build_job_id(stamp, source_key)
    request_id = build_request_id(stamp, source_key, "answer")
    result = result_path(root, job_id, "answer")
    request = write_generation_request(
        root,
        job_id,
        "answer",
        {
            "request_id": request_id,
            "job_id": job_id,
            "generation_type": "answer",
            "question": question,
            "save": save,
            "source_paths": source_paths,
            "prompt_path": "prompts/answer.md",
            "output_schema": "answer_v1",
            "result_path": result.relative_to(root).as_posix(),
        },
        "## 任务\n\n请基于 `source_paths` 回答问题，并为每个主要结论提供引用。\n\n"
        "## 输出要求\n\n只写入 `result_path`，引用不得超出 `source_paths`。\n",
    )
    write_job(
        root,
        job_id,
        {
            "job_id": job_id,
            "generation_type": "answer",
            "question": question,
            "save": save,
            "source_paths": source_paths,
            "status": "needs_generation",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        },
    )
    return {
        "ok": True,
        "command": "kb ask",
        "status": "needs_generation",
        "job_id": job_id,
        "source_paths": source_paths,
        "generation_request_path": request.relative_to(root).as_posix(),
        "generation_result_path": result.relative_to(root).as_posix(),
        "next_action": "write_generation_result",
        "message": "Answer generation request created.",
    }


def _rebuild_insights_index(root: Path) -> Path:
    return write_insights_index(
        root,
        [
            (str(post.metadata.get("title", path.stem)), path.relative_to(root).as_posix())
            for path, post in iter_insights(root)
        ],
    )


def continue_answer(root: Path, job_id: str) -> dict:
    try:
        job = read_job(root, job_id)
    except FileNotFoundError:
        return error_response(
            command="kb ask --continue",
            status="permanent_failed",
            error_code="JOB_NOT_FOUND",
            error_message="Job file does not exist.",
            retryable=False,
            next_action="none",
            job_id=job_id,
        )
    if job.get("generation_type") != "answer":
        return error_response(
            command="kb ask --continue",
            status="permanent_failed",
            error_code="GENERATION_TYPE_MISMATCH",
            error_message="Job generation type is not answer.",
            retryable=False,
            next_action="none",
            job_id=job_id,
        )
    try:
        result = read_generation_result(root, job_id, "answer")
    except FileNotFoundError:
        return error_response(
            command="kb ask --continue",
            status="failed",
            error_code="GENERATION_RESULT_NOT_FOUND",
            error_message="Generation result file does not exist.",
            retryable=True,
            next_action="write_generation_result",
            job_id=job_id,
        )
    except (ValidationError, ValueError) as exc:
        return error_response(
            command="kb ask --continue",
            status="failed",
            error_code="GENERATION_RESULT_INVALID",
            error_message=str(exc),
            retryable=True,
            next_action="write_generation_result",
            job_id=job_id,
        )
    payload = result.payload
    if not isinstance(payload, AnswerPayload) or payload.question != job["question"]:
        return error_response(
            command="kb ask --continue",
            status="failed",
            error_code="ANSWER_QUESTION_MISMATCH",
            error_message="Answer question does not match job question.",
            retryable=True,
            next_action="write_generation_result",
            job_id=job_id,
        )
    allowed_sources = set(job["source_paths"])
    if any(citation.path not in allowed_sources for citation in payload.citations):
        return error_response(
            command="kb ask --continue",
            status="failed",
            error_code="ANSWER_CITATION_INVALID",
            error_message="Answer citation is outside request source_paths.",
            retryable=True,
            next_action="write_generation_result",
            job_id=job_id,
        )

    insight_path = None
    if job.get("save"):
        insight_path = write_insight(root, payload, result.created_at)
        _rebuild_insights_index(root)
    append_history(
        root,
        "ask",
        payload.title,
        [
            f"job_id: {job_id}",
            f"saved: {bool(insight_path)}",
            *([f"insight: {insight_path.relative_to(root).as_posix()}"] if insight_path else []),
        ],
    )
    return {
        "ok": True,
        "command": "kb ask --continue",
        "status": "completed",
        "job_id": job_id,
        "title": payload.title,
        "answer_markdown": payload.answer_markdown,
        "citations": [citation.model_dump() for citation in payload.citations],
        "insight_path": insight_path.relative_to(root).as_posix() if insight_path else None,
        "next_action": "none",
        "message": "Answer completed.",
    }
