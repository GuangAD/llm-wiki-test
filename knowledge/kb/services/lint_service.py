import re
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from kb.core.errors import error_response
from kb.core.ids import build_job_id, build_request_id
from kb.core.models import LintIssue, LintPayload
from kb.storage.generation_store import read_generation_result, result_path, write_generation_request
from kb.storage.insight_store import iter_insights
from kb.storage.job_store import read_job, write_job
from kb.storage.log_store import append_history
from kb.storage.note_store import iter_notes
from kb.storage.report_store import write_lint_report
from kb.storage.topic_store import iter_topics


LINK_RE = re.compile(r"\[[^\]]+\]\((?P<target>[^)]+)\)")


def _issue(code: str, severity: str, paths: list[str], description: str, action: str) -> dict:
    return {
        "code": code,
        "severity": severity,
        "target_paths": paths,
        "description": description,
        "suggested_action": action,
    }


def deterministic_issues(root: Path) -> list[dict]:
    issues: list[dict] = []
    notes = iter_notes(root)
    topics = iter_topics(root)
    insights = iter_insights(root)
    note_ids = {str(post.metadata.get("id", path.stem)) for path, post in notes}

    seen_ids: dict[str, str] = {}
    for path, post in [*notes, *topics, *insights]:
        rel_path = path.relative_to(root).as_posix()
        item_id = str(
            post.metadata.get("id")
            or post.metadata.get("topic_key")
            or post.metadata.get("question")
            or ""
        )
        if not item_id:
            issues.append(
                _issue(
                    "missing_identity",
                    "error",
                    [rel_path],
                    "知识文件缺少稳定身份字段。",
                    "补齐 id、topic_key 或 question 后重新检查。",
                )
            )
        elif item_id in seen_ids:
            issues.append(
                _issue(
                    "duplicate_identity",
                    "error",
                    [seen_ids[item_id], rel_path],
                    "多个知识文件使用了相同身份字段。",
                    "保留唯一身份并重新构建索引。",
                )
            )
        else:
            seen_ids[item_id] = rel_path

    for path, post in topics:
        rel_path = path.relative_to(root).as_posix()
        missing = [
            str(note_id)
            for note_id in post.metadata.get("source_note_ids", [])
            if str(note_id) not in note_ids
        ]
        if missing:
            issue = _issue(
                "missing_topic_source",
                "error",
                [rel_path],
                f"主题页引用了不存在的 Note：{', '.join(missing)}。",
                "修复来源后重新编译主题。",
            )
            issue["topic_key"] = str(post.metadata.get("topic_key", "")) or None
            issues.append(issue)

    for index_path in sorted((root / "indexes").glob("*.md")):
        for match in LINK_RE.finditer(index_path.read_text(encoding="utf-8")):
            target = match.group("target")
            if target.startswith(("http://", "https://")):
                continue
            resolved = (index_path.parent / target).resolve()
            if not resolved.exists():
                issues.append(
                    _issue(
                        "broken_index_link",
                        "error",
                        [index_path.relative_to(root).as_posix()],
                        f"索引链接目标不存在：{target}。",
                        "重建对应索引。",
                    )
                )

    topic_index = (root / "indexes" / "topics.md")
    topic_index_text = topic_index.read_text(encoding="utf-8") if topic_index.exists() else ""
    for path, _ in topics:
        rel_path = path.relative_to(root).as_posix()
        if path.name not in topic_index_text:
            issues.append(
                _issue(
                    "wiki_not_indexed",
                    "warning",
                    [rel_path],
                    "主题页没有出现在 topics 索引中。",
                    "重新构建主题索引。",
                )
            )
    insight_index = root / "indexes" / "insights.md"
    insight_index_text = insight_index.read_text(encoding="utf-8") if insight_index.exists() else ""
    for path, _ in insights:
        rel_path = path.relative_to(root).as_posix()
        if path.name not in insight_index_text:
            issues.append(
                _issue(
                    "wiki_not_indexed",
                    "warning",
                    [rel_path],
                    "Insight 没有出现在 insights 索引中。",
                    "重新构建 Insight 索引。",
                )
            )
    return issues


def _source_paths(root: Path) -> list[str]:
    paths = [*sorted((root / "indexes").glob("*.md"))]
    paths.extend(path for path, _ in iter_topics(root))
    paths.extend(path for path, _ in iter_insights(root))
    paths.extend(path for path, _ in iter_notes(root))
    return [path.relative_to(root).as_posix() for path in paths]


def request_lint(root: Path) -> dict:
    now = datetime.now().astimezone()
    stamp = now.strftime("%Y%m%d%H%M%S")
    source_key = f"lint:{now.isoformat()}"
    job_id = build_job_id(stamp, source_key)
    request_id = build_request_id(stamp, source_key, "lint")
    source_paths = _source_paths(root)
    findings = deterministic_issues(root)
    result = result_path(root, job_id, "lint")
    request = write_generation_request(
        root,
        job_id,
        "lint",
        {
            "request_id": request_id,
            "job_id": job_id,
            "generation_type": "lint",
            "source_paths": source_paths,
            "deterministic_issues": findings,
            "prompt_path": "prompts/lint.md",
            "output_schema": "lint_v1",
            "result_path": result.relative_to(root).as_posix(),
        },
        "## 任务\n\n请结合确定性检查和 `source_paths` 检查语义矛盾、过时结论、"
        "缺少交叉引用和缺失主题。\n\n"
        "## 输出要求\n\n只写入 `result_path`，不要直接修改知识文件。\n",
    )
    write_job(
        root,
        job_id,
        {
            "job_id": job_id,
            "generation_type": "lint",
            "deterministic_issues": findings,
            "status": "needs_generation",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        },
    )
    return {
        "ok": True,
        "command": "kb lint",
        "status": "needs_generation",
        "job_id": job_id,
        "deterministic_issue_count": len(findings),
        "generation_request_path": request.relative_to(root).as_posix(),
        "generation_result_path": result.relative_to(root).as_posix(),
        "next_action": "write_generation_result",
        "message": "Lint generation request created.",
    }


def continue_lint(root: Path, job_id: str) -> dict:
    try:
        job = read_job(root, job_id)
    except FileNotFoundError:
        return error_response(
            command="kb lint --continue",
            status="permanent_failed",
            error_code="JOB_NOT_FOUND",
            error_message="Job file does not exist.",
            retryable=False,
            next_action="none",
            job_id=job_id,
        )
    if job.get("generation_type") != "lint":
        return error_response(
            command="kb lint --continue",
            status="permanent_failed",
            error_code="GENERATION_TYPE_MISMATCH",
            error_message="Job generation type is not lint.",
            retryable=False,
            next_action="none",
            job_id=job_id,
        )
    try:
        result = read_generation_result(root, job_id, "lint")
    except FileNotFoundError:
        return error_response(
            command="kb lint --continue",
            status="failed",
            error_code="GENERATION_RESULT_NOT_FOUND",
            error_message="Generation result file does not exist.",
            retryable=True,
            next_action="write_generation_result",
            job_id=job_id,
        )
    except (ValidationError, ValueError) as exc:
        return error_response(
            command="kb lint --continue",
            status="failed",
            error_code="GENERATION_RESULT_INVALID",
            error_message=str(exc),
            retryable=True,
            next_action="write_generation_result",
            job_id=job_id,
        )
    payload = result.payload
    if not isinstance(payload, LintPayload):
        return error_response(
            command="kb lint --continue",
            status="failed",
            error_code="GENERATION_RESULT_INVALID",
            error_message="Generation result is not a lint payload.",
            retryable=True,
            next_action="write_generation_result",
            job_id=job_id,
        )
    issues = [LintIssue.model_validate(item) for item in job.get("deterministic_issues", [])]
    issues.extend(payload.issues)
    report_path = write_lint_report(root, result.created_at, payload.summary, issues)
    append_history(
        root,
        "lint",
        "知识库健康检查",
        [
            f"job_id: {job_id}",
            f"report: {report_path.relative_to(root).as_posix()}",
            f"issues: {len(issues)}",
        ],
    )
    return {
        "ok": True,
        "command": "kb lint --continue",
        "status": "completed",
        "job_id": job_id,
        "report_path": report_path.relative_to(root).as_posix(),
        "issue_count": len(issues),
        "next_action": "none",
        "message": "Lint report persisted. Knowledge files were not modified.",
    }
