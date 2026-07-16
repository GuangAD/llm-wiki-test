from datetime import datetime
from hashlib import sha256
from pathlib import Path

import yaml
from pydantic import ValidationError

from kb.adapters.registry import adapt_input
from kb.core.errors import error_response
from kb.core.ids import (
    build_content_id,
    build_job_id,
    build_note_id_from_content_id,
    build_request_id,
)
from kb.core.locks import IngestLockedError, ingest_lock
from kb.storage.generation_store import read_generation_result, result_path, write_generation_request
from kb.storage.index_store import write_phase1_indexes
from kb.storage.job_store import read_job, write_job
from kb.storage.log_store import append_history
from kb.storage.note_store import iter_notes, write_note
from kb.storage.raw_store import find_existing_content_by_hash, write_raw
from kb.services.relation_service import sync_relations


def _now() -> datetime:
    return datetime.now().astimezone()


def ingest_first_pass(root: Path, value: str) -> dict:
    try:
        with ingest_lock(root):
            return _ingest_first_pass_locked(root, value)
    except IngestLockedError as exc:
        return error_response(
            command="kb ingest",
            status="failed",
            error_code="INGEST_LOCKED",
            error_message=str(exc),
            retryable=True,
            next_action="retry",
        )


def _ingest_first_pass_locked(root: Path, value: str) -> dict:
    now = _now()
    date = now.strftime("%Y%m%d")
    stamp = now.strftime("%Y%m%d%H%M%S")
    content = adapt_input(value)
    content_hash = f"sha256:{sha256(content.text.encode('utf-8')).hexdigest()}"
    existing = find_existing_content_by_hash(root, content_hash)
    if existing:
        content_id, meta_path = existing
        return {
            "ok": True,
            "command": "kb ingest",
            "status": "duplicate",
            "content_id": content_id,
            "existing_meta_path": str(meta_path.relative_to(root)),
            "next_action": "none",
            "message": "Content already exists.",
        }

    source_key = content.source_uri
    content_id = build_content_id(date, source_key)
    job_id = build_job_id(stamp, source_key)
    request_id = build_request_id(stamp, source_key, "note")
    raw_path, _ = write_raw(
        root,
        date,
        content_id,
        content.text,
        yaml.safe_dump(
            {
                "id": content_id,
                "source_type": content.source_type,
                "source_uri": content.source_uri,
                "source_title": content.title,
                "captured_at": now.isoformat(),
                "content_hash": content_hash,
                "mime_type": content.mime_type,
                "status": "active",
            },
            allow_unicode=True,
            sort_keys=False,
        ),
    )
    known_topic_keys = sorted(
        {
            str(key)
            for _, post in iter_notes(root)
            for key in post.metadata.get("topic_keys", [])
        }
    )
    result = result_path(root, job_id, "note")
    request = write_generation_request(
        root,
        job_id,
        "note",
        {
            "request_id": request_id,
            "job_id": job_id,
            "content_id": content_id,
            "generation_type": "note",
            "source_paths": [raw_path.relative_to(root).as_posix()],
            "prompt_path": "prompts/note.md",
            "output_schema": "note_v1",
            "known_topic_keys": known_topic_keys,
            "result_path": str(result.relative_to(root)),
        },
        "## 任务\n\n"
        "请读取 `source_paths` 中的原文，生成一份结构化 note 结果。"
        "语义相同的主题优先复用 `known_topic_keys`。\n\n"
        "## 输出要求\n\n"
        "只写入 `result_path`，不要直接修改 `notes/`、`indexes/`、`wiki/`。\n",
    )
    write_job(
        root,
        job_id,
        {
            "job_id": job_id,
            "content_id": content_id,
            "status": "needs_generation",
            "current_stage": "generation_requested",
            "completed_stages": ["received", "raw_saved", "generation_requested"],
            "retry_count": 0,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        },
    )
    return {
        "ok": True,
        "command": "kb ingest",
        "status": "needs_generation",
        "job_id": job_id,
        "content_id": content_id,
        "next_action": "write_generation_result",
            "generation_request_path": request.relative_to(root).as_posix(),
            "generation_result_path": result.relative_to(root).as_posix(),
        "message": "Generation request created. Read request file and write result file.",
    }


def ingest_continue(root: Path, job_id: str) -> dict:
    try:
        job = read_job(root, job_id)
    except FileNotFoundError:
        return error_response(
            command="kb ingest --continue",
            status="permanent_failed",
            error_code="JOB_NOT_FOUND",
            error_message="Job file does not exist.",
            retryable=False,
            next_action="none",
            job_id=job_id,
        )

    try:
        result = read_generation_result(root, job_id, "note")
    except FileNotFoundError:
        return error_response(
            command="kb ingest --continue",
            status="failed",
            error_code="GENERATION_RESULT_NOT_FOUND",
            error_message="Generation result file does not exist.",
            retryable=True,
            next_action="write_generation_result",
            job_id=job_id,
        )
    except (ValidationError, ValueError) as exc:
        return error_response(
            command="kb ingest --continue",
            status="failed",
            error_code="GENERATION_RESULT_INVALID",
            error_message=str(exc),
            retryable=True,
            next_action="write_generation_result",
            job_id=job_id,
        )

    date = result.content_id.split("_")[1]
    note_id = build_note_id_from_content_id(result.content_id)
    source = result.sources[0] if result.sources else None
    metadata = {
        "id": note_id,
        "content_id": result.content_id,
        "title": result.payload.title,
        "source_type": "text",
        "source_uri": source.source_uri if source else None,
        "created_at": result.created_at,
        "tags": result.payload.tags,
        "summary": result.payload.summary,
        "stance": result.payload.stance.value,
        "related_note_ids": [],
        "topic_keys": [],
        "status": "active",
    }
    body = "\n\n".join(
        [
            f"## 摘要\n\n{result.payload.summary}",
            "## 关键信息\n\n" + "\n".join(f"- {item}" for item in result.payload.key_points),
            f"## 我的判断\n\n{result.payload.my_judgement}",
            "## 可用场景\n\n" + "\n".join(f"- {item}" for item in result.payload.useful_for),
            "## 主题候选\n\n" + "\n".join(f"- {item}" for item in result.payload.related_topics),
        ]
    )
    note_path = write_note(root, date, note_id, metadata, body)
    relation_result = sync_relations(root, note_id, result.payload.related_topics)
    topic_request_paths = _write_topic_requests(root, job_id, relation_result["compilable_topic_keys"])
    index_paths = rebuild_phase1_indexes(root)
    completed_stages = [
        *job.get("completed_stages", []),
        "generation_completed",
        "note_generated",
        "indexes_updated",
        "completed",
    ]
    write_job(
        root,
        job_id,
        {
            **job,
            "status": "completed",
            "current_stage": "completed",
            "completed_stages": list(dict.fromkeys(completed_stages)),
            "updated_at": _now().isoformat(),
        },
    )
    append_history(
        root,
        "ingest",
        result.payload.title,
        [
            f"job_id: {job_id}",
            f"note: {note_path.relative_to(root).as_posix()}",
            f"content_id: {result.content_id}",
        ],
    )
    return {
        "ok": True,
        "command": "kb ingest --continue",
        "status": "completed",
        "job_id": job_id,
        "note_path": note_path.relative_to(root).as_posix(),
        "index_paths": [path.relative_to(root).as_posix() for path in index_paths],
        "related_note_ids": relation_result["related_note_ids"],
        "topic_request_paths": [path.relative_to(root).as_posix() for path in topic_request_paths],
        "next_action": "write_generation_result" if topic_request_paths else "none",
        "message": "Note persisted and indexes updated.",
    }


def _write_topic_requests(root: Path, job_id: str, topic_keys: list[str]) -> list[Path]:
    paths: list[Path] = []
    stamp = job_id.split("_", maxsplit=2)[1]
    notes = iter_notes(root)
    for topic_key in topic_keys:
        source_paths = [
            path.relative_to(root).as_posix()
            for path, post in notes
            if topic_key in [str(key) for key in post.metadata.get("topic_keys", [])]
        ]
        result = result_path(root, job_id, "topic", topic_key)
        request = write_generation_request(
            root,
            job_id,
            "topic",
            {
                "request_id": f"gen_{stamp}_{topic_key}_topic",
                "job_id": job_id,
                "generation_type": "topic",
                "topic_key": topic_key,
                "source_paths": source_paths,
                "prompt_path": "prompts/topic.md",
                "output_schema": "topic_v1",
                "result_path": result.relative_to(root).as_posix(),
            },
            "## 任务\n\n"
            f"请读取 `source_paths` 中的 note，生成主题 `{topic_key}` 的结构化 topic 结果。\n\n"
            "## 输出要求\n\n"
            "只写入 `result_path`，不要直接修改 `wiki/`、`indexes/`。\n",
            scope_key=topic_key,
        )
        paths.append(request)
    return paths


def rebuild_phase1_indexes(root: Path) -> list[Path]:
    notes = iter_notes(root)
    recent_lines = ["# Recent", ""]
    tag_map: dict[str, list[str]] = {}
    source_lines = ["# Sources", ""]

    for path, post in notes:
        note_id = str(post.metadata.get("id", path.stem))
        title = str(post.metadata.get("title", path.stem))
        rel_path = path.relative_to(root).as_posix()
        recent_lines.append(f"- [{title}](../{rel_path})")
        for tag in post.metadata.get("tags", []):
            tag_map.setdefault(str(tag), []).append(note_id)
        source_uri = post.metadata.get("source_uri")
        if source_uri:
            source_lines.append(f"- {source_uri}: {note_id}")

    tag_lines = ["# Tags", ""]
    for tag in sorted(tag_map):
        tag_lines.append(f"- {tag}: {', '.join(tag_map[tag])}")

    return write_phase1_indexes(
        root,
        "\n".join(recent_lines) + "\n",
        "\n".join(tag_lines) + "\n",
        "\n".join(source_lines) + "\n",
    )
