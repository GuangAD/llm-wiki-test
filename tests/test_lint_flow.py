import json

import frontmatter
import yaml
from typer.testing import CliRunner

from kb.cli.main import app


def test_lint_writes_report_without_modifying_topic(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    runner = CliRunner()
    runner.invoke(app, ["init"])
    topic_path = workspace / "wiki" / "topic-ai.md"
    original = frontmatter.dumps(
        frontmatter.Post(
            "旧结论",
            topic_key="ai",
            title="AI",
            source_note_ids=["missing_note"],
            updated_at="2026-06-22T10:00:00+08:00",
        )
    )
    topic_path.write_text(original, encoding="utf-8")

    first = runner.invoke(app, ["lint"])
    first_data = json.loads(first.stdout)
    request = frontmatter.loads(
        (workspace / first_data["generation_request_path"]).read_text(encoding="utf-8")
    )
    (workspace / first_data["generation_result_path"]).write_text(
        yaml.safe_dump(
            {
                "request_id": request.metadata["request_id"],
                "job_id": first_data["job_id"],
                "generation_type": "lint",
                "status": "completed",
                "created_at": "2026-06-22T12:00:00+08:00",
                "sources": [{"path": "wiki/topic-ai.md"}],
                "payload": {
                    "summary": "主题存在来源和时效问题。",
                    "issues": [
                        {
                            "code": "stale_claim",
                            "severity": "warning",
                            "target_paths": ["wiki/topic-ai.md"],
                            "description": "旧结论需要重新核对。",
                            "suggested_action": "重新编译主题。",
                            "topic_key": "ai",
                        }
                    ],
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    second = runner.invoke(app, ["lint", "--continue", first_data["job_id"]])
    second_data = json.loads(second.stdout)
    report = workspace / second_data["report_path"]

    assert second_data["status"] == "completed"
    assert second_data["issue_count"] >= 2
    assert topic_path.read_text(encoding="utf-8") == original
    assert "uv run kb compile --topic-key ai" in report.read_text(encoding="utf-8")
