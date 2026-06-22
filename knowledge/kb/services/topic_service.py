from pathlib import Path

from pydantic import ValidationError

from kb.core.errors import error_response
from kb.core.models import TopicPayload
from kb.storage.generation_store import read_generation_result
from kb.storage.index_store import write_topics_index
from kb.storage.topic_store import iter_topics, write_topic


def compile_continue(root: Path, job_id: str, topic_key: str) -> dict:
    try:
        result = read_generation_result(root, job_id, "topic")
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
    except ValidationError as exc:
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
