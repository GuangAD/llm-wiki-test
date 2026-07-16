from pathlib import Path

from kb.core.atomic import atomic_write_text
from kb.core.models import LintIssue


def write_lint_report(
    root: Path,
    created_at: str,
    summary: str,
    issues: list[LintIssue],
) -> Path:
    stamp = created_at[:19].replace("-", "").replace(":", "").replace("T", "")
    path = root / "reports" / f"lint-{stamp}.md"
    lines = [
        "---",
        "type: lint_report",
        f"created_at: {created_at}",
        f"issue_count: {len(issues)}",
        "---",
        "",
        "# 知识库健康检查",
        "",
        "## 摘要",
        "",
        summary,
        "",
        "## 问题",
        "",
    ]
    if not issues:
        lines.append("未发现问题。")
    for issue in issues:
        lines.extend(
            [
                f"### [{issue.severity}] {issue.code}",
                "",
                issue.description,
                "",
                "目标：",
                *[f"- `{target}`" for target in issue.target_paths],
                "",
                f"建议：{issue.suggested_action}",
            ]
        )
        if issue.topic_key:
            lines.extend(
                [
                    "",
                    "修复命令：",
                    "",
                    f"`uv run kb compile --topic-key {issue.topic_key}`",
                ]
            )
        lines.append("")
    atomic_write_text(path, "\n".join(lines))
    return path
