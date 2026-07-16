from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from kb.core.errors import error_response
from kb.core.ids import build_job_id, build_request_id
from kb.core.models import TopicPayload
from kb.storage.generation_store import read_generation_result, result_path, write_generation_request
from kb.storage.index_store import write_topics_index
from kb.storage.job_store import write_job
from kb.storage.log_store import append_history
from kb.storage.note_store import iter_notes
from kb.storage.topic_store import iter_topics, write_topic


def request_compile(root: Path, topic_key: str) -> dict:
    now = datetime.now().astimezone()
    stamp = now.strftime("%Y%m%d%H%M%S")
    source_key = f"topic:{topic_key}:{now.isoformat()}"
    job_id = build_job_id(stamp, source_key)
    request_id = build_request_id(stamp, source_key, "topic")
    source_paths = [
        path.relative_to(root).as_posix()
        for path, post in iter_notes(root)
        if topic_key in [str(key) for key in post.metadata.get("topic_keys", [])]
    ]
    existing_topic = root / "wiki" / f"topic-{topic_key}.md"
    if existing_topic.exists():
        source_paths.append(existing_topic.relative_to(root).as_posix())
    if len([path for path in source_paths if path.startswith("notes/")]) < 2:
        return error_response(
            command="kb compile",
            status="permanent_failed",
            error_code="TOPIC_NOT_READY",
            error_message="At least two notes are required to compile a topic.",
            retryable=False,
            next_action="none",
        )

    result = result_path(root, job_id, "topic", topic_key)
    request = write_generation_request(
        root,
        job_id,
        "topic",
        {
            "request_id": request_id,
            "job_id": job_id,
            "generation_type": "topic",
            "topic_key": topic_key,
            "source_paths": source_paths,
            "prompt_path": "prompts/topic.md",
            "output_schema": "topic_v1",
            "result_path": result.relative_to(root).as_posix(),
        },
        "## 任务\n\n"
        f"请读取 `source_paths`，重新编译主题 `{topic_key}`。已有主题页只能作为旧版本参考。\n\n"
        "## 输出要求\n\n只写入 `result_path`，不要直接修改 `wiki/`、`indexes/`。\n",
        scope_key=topic_key,
    )
    write_job(
        root,
        job_id,
        {
            "job_id": job_id,
            "generation_type": "topic",
            "topic_key": topic_key,
            "status": "needs_generation",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        },
    )
    return {
        "ok": True,
        "command": "kb compile",
        "status": "needs_generation",
        "job_id": job_id,
        "topic_key": topic_key,
        "generation_request_path": request.relative_to(root).as_posix(),
        "generation_result_path": result.relative_to(root).as_posix(),
        "next_action": "write_generation_result",
        "message": "Topic generation request created.",
    }


def compile_continue(root: Path, job_id: str, topic_key: str) -> dict:
    try:
        result = read_generation_result(root, job_id, "topic", topic_key)
    except FileNotFoundError:
        return error_response(
            command="kb compile --continue",
            status="failed",
            error_code="GENERATION_RESULT_NOT_FOUND",
            error_message="Generation result file does not exist.",
            retryable=True,
            next_action="write_generation_result",
            job_id=job_id,
        )
    except (ValidationError, ValueError) as exc:
        return error_response(
            command="kb compile --continue",
            status="failed",
            error_code="GENERATION_RESULT_INVALID",
            error_message=str(exc),
            retryable=True,
            next_action="write_generation_result",
            job_id=job_id,
        )

    payload = result.payload
    if not isinstance(payload, TopicPayload):
        return error_response(
            command="kb compile --continue",
            status="failed",
            error_code="GENERATION_RESULT_INVALID",
            error_message="Generation result is not a topic payload.",
            retryable=True,
            next_action="write_generation_result",
            job_id=job_id,
        )
    if payload.topic_key != topic_key:
        return error_response(
            command="kb compile --continue",
            status="failed",
            error_code="TOPIC_KEY_MISMATCH",
            error_message="Topic key in result does not match command argument.",
            retryable=True,
            next_action="write_generation_result",
            job_id=job_id,
        )

    topic_path = write_topic(root, payload, result.created_at)
    index_path = rebuild_topics_index(root)
    append_history(
        root,
        "compile",
        payload.title,
        [f"topic_key: {topic_key}", f"path: {topic_path.relative_to(root).as_posix()}"],
    )
    return {
        "ok": True,
        "command": "kb compile --continue",
        "status": "completed",
        "job_id": job_id,
        "topic_key": topic_key,
        "topic_path": topic_path.relative_to(root).as_posix(),
        "index_path": index_path.relative_to(root).as_posix(),
        "next_action": "none",
        "message": "Topic page persisted and topics index updated.",
    }


def rebuild_topics_index(root: Path) -> Path:
    topics = []
    for path, post in iter_topics(root):
        topics.append(
            (
                str(post.metadata.get("title", path.stem)),
                str(post.metadata.get("topic_key", path.stem.removeprefix("topic-"))),
                path.relative_to(root).as_posix(),
            )
        )
    return write_topics_index(root, topics)
