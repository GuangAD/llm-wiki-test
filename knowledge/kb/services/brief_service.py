from datetime import datetime
from pathlib import Path

import frontmatter
from pydantic import ValidationError

from kb.core.errors import error_response
from kb.core.ids import build_job_id, build_request_id
from kb.core.models import BriefTopicsPayload, BriefWeeklyPayload
from kb.storage.brief_store import write_topic_picks, write_weekly
from kb.storage.generation_store import read_generation_result, result_path, write_generation_request
from kb.storage.job_store import read_job, write_job
from kb.storage.log_store import append_history


def _now() -> datetime:
    return datetime.now().astimezone()


def _belongs_to_week(path: Path, target_week: str) -> bool:
    post = frontmatter.loads(path.read_text(encoding="utf-8"))
    value = post.metadata.get("created_at") or post.metadata.get("updated_at")
    if not value:
        return False
    try:
        created = datetime.fromisoformat(str(value))
    except ValueError:
        return False
    year, week, _ = created.isocalendar()
    return f"{year}-W{week:02d}" == target_week


def _source_paths(root: Path, target_week: str | None = None) -> list[str]:
    if target_week:
        candidates = [
            *sorted((root / "wiki").glob("*.md")),
            *sorted((root / "notes").glob("**/*.md")),
        ]
        candidates = [path for path in candidates if _belongs_to_week(path, target_week)]
    else:
        candidates = [
            root / "indexes" / "topics.md",
            root / "indexes" / "insights.md",
            root / "indexes" / "recent.md",
            root / "indexes" / "tags.md",
        ]
        candidates.extend(sorted((root / "wiki").glob("*.md")))
        candidates.extend(sorted((root / "notes").glob("**/*.md")))
    return [path.relative_to(root).as_posix() for path in candidates if path.exists()]


def request_brief_topics(root: Path) -> dict:
    now = _now()
    date = now.strftime("%Y-%m-%d")
    stamp = now.strftime("%Y%m%d%H%M%S")
    source_key = f"brief_topics:{date}:{now.isoformat()}"
    job_id = build_job_id(stamp, source_key)
    request_id = build_request_id(stamp, source_key, "brief_topics")
    result = result_path(root, job_id, "brief_topics")
    request = write_generation_request(
        root,
        job_id,
        "brief_topics",
        {
            "request_id": request_id,
            "job_id": job_id,
            "generation_type": "brief_topics",
            "date": date,
            "source_paths": _source_paths(root),
            "prompt_path": "prompts/brief-topics.md",
            "output_schema": "brief_topics_v1",
            "result_path": result.relative_to(root).as_posix(),
        },
        "## 任务\n\n请根据 `source_paths` 生成结构化选题清单。\n\n"
        "## 输出要求\n\n只写入 `result_path`，不要直接修改 `briefs/`。\n",
    )
    write_job(
        root,
        job_id,
        {
            "job_id": job_id,
            "status": "needs_generation",
            "generation_type": "brief_topics",
            "target_date": date,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        },
    )
    return _request_response("brief_topics", job_id, request_id, request, result, date=date)


def request_brief_weekly(root: Path) -> dict:
    now = _now()
    year, week, _ = now.isocalendar()
    target_week = f"{year}-W{week:02d}"
    stamp = now.strftime("%Y%m%d%H%M%S")
    source_key = f"brief_weekly:{target_week}:{now.isoformat()}"
    job_id = build_job_id(stamp, source_key)
    request_id = build_request_id(stamp, source_key, "brief_weekly")
    result = result_path(root, job_id, "brief_weekly")
    request = write_generation_request(
        root,
        job_id,
        "brief_weekly",
        {
            "request_id": request_id,
            "job_id": job_id,
            "generation_type": "brief_weekly",
            "week": target_week,
            "source_paths": _source_paths(root, target_week),
            "prompt_path": "prompts/brief-weekly.md",
            "output_schema": "brief_weekly_v1",
            "result_path": result.relative_to(root).as_posix(),
        },
        "## 任务\n\n请根据 `source_paths` 生成结构化知识周报。\n\n"
        "## 输出要求\n\n只写入 `result_path`，不要直接修改 `briefs/`。\n",
    )
    write_job(
        root,
        job_id,
        {
            "job_id": job_id,
            "status": "needs_generation",
            "generation_type": "brief_weekly",
            "target_week": target_week,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        },
    )
    return _request_response("brief_weekly", job_id, request_id, request, result, week=target_week)


def _request_response(
    generation_type: str,
    job_id: str,
    request_id: str,
    request: Path,
    result: Path,
    **extra: str,
) -> dict:
    return {
        "ok": True,
        "command": f"kb brief {generation_type.removeprefix('brief_')}",
        "status": "needs_generation",
        "generation_type": generation_type,
        "job_id": job_id,
        "request_id": request_id,
        "generation_request_path": request.relative_to(request.parents[2]).as_posix(),
        "generation_result_path": result.relative_to(result.parents[2]).as_posix(),
        "next_action": "write_generation_result",
        "message": "Generation request created. Read request file and write result file.",
        **extra,
    }


def continue_brief_topics(root: Path, job_id: str) -> dict:
    job = _read_brief_job(root, job_id, "brief_topics")
    if "ok" in job and job["ok"] is False:
        return job
    result_or_error = _read_brief_result(root, job_id, "brief_topics")
    if isinstance(result_or_error, dict):
        return result_or_error
    result = result_or_error
    payload = result.payload
    if not isinstance(payload, BriefTopicsPayload):
        return _invalid_payload(job_id, "brief_topics")
    if payload.date != job["target_date"]:
        return error_response(
            command="kb brief topics --continue",
            status="failed",
            error_code="BRIEF_DATE_MISMATCH",
            error_message="Brief date in result does not match job target date.",
            retryable=True,
            next_action="write_generation_result",
            job_id=job_id,
        )
    brief_path = write_topic_picks(root, payload, result.created_at)
    return _completed_response("kb brief topics --continue", job_id, brief_path, root)


def continue_brief_weekly(root: Path, job_id: str) -> dict:
    job = _read_brief_job(root, job_id, "brief_weekly")
    if "ok" in job and job["ok"] is False:
        return job
    result_or_error = _read_brief_result(root, job_id, "brief_weekly")
    if isinstance(result_or_error, dict):
        return result_or_error
    result = result_or_error
    payload = result.payload
    if not isinstance(payload, BriefWeeklyPayload):
        return _invalid_payload(job_id, "brief_weekly")
    if payload.week != job["target_week"]:
        return error_response(
            command="kb brief weekly --continue",
            status="failed",
            error_code="BRIEF_WEEK_MISMATCH",
            error_message="Brief week in result does not match job target week.",
            retryable=True,
            next_action="write_generation_result",
            job_id=job_id,
        )
    brief_path = write_weekly(root, payload, result.created_at)
    return _completed_response("kb brief weekly --continue", job_id, brief_path, root)


def _read_brief_job(root: Path, job_id: str, generation_type: str) -> dict:
    try:
        job = read_job(root, job_id)
    except FileNotFoundError:
        return error_response(
            command=f"kb brief {generation_type.removeprefix('brief_')} --continue",
            status="permanent_failed",
            error_code="JOB_NOT_FOUND",
            error_message="Job file does not exist.",
            retryable=False,
            next_action="none",
            job_id=job_id,
        )
    if job.get("generation_type") != generation_type:
        return error_response(
            command=f"kb brief {generation_type.removeprefix('brief_')} --continue",
            status="failed",
            error_code="GENERATION_TYPE_MISMATCH",
            error_message="Job generation type does not match command.",
            retryable=False,
            next_action="none",
            job_id=job_id,
        )
    return job


def _read_brief_result(root: Path, job_id: str, generation_type: str):
    try:
        return read_generation_result(root, job_id, generation_type)
    except FileNotFoundError:
        return error_response(
            command=f"kb brief {generation_type.removeprefix('brief_')} --continue",
            status="failed",
            error_code="GENERATION_RESULT_NOT_FOUND",
            error_message="Generation result file does not exist.",
            retryable=True,
            next_action="write_generation_result",
            job_id=job_id,
        )
    except (ValidationError, ValueError) as exc:
        return error_response(
            command=f"kb brief {generation_type.removeprefix('brief_')} --continue",
            status="failed",
            error_code="GENERATION_RESULT_INVALID",
            error_message=str(exc),
            retryable=True,
            next_action="write_generation_result",
            job_id=job_id,
        )


def _invalid_payload(job_id: str, generation_type: str) -> dict:
    return error_response(
        command=f"kb brief {generation_type.removeprefix('brief_')} --continue",
        status="failed",
        error_code="GENERATION_RESULT_INVALID",
        error_message="Generation result payload does not match command.",
        retryable=True,
        next_action="write_generation_result",
        job_id=job_id,
    )


def _completed_response(command: str, job_id: str, brief_path: Path, root: Path) -> dict:
    append_history(
        root,
        "brief",
        brief_path.stem,
        [f"job_id: {job_id}", f"path: {brief_path.relative_to(root).as_posix()}"],
    )
    return {
        "ok": True,
        "command": command,
        "status": "completed",
        "job_id": job_id,
        "brief_path": brief_path.relative_to(root).as_posix(),
        "next_action": "none",
        "message": "Brief persisted.",
    }
