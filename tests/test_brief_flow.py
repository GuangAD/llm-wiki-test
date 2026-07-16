import json
from datetime import datetime

import frontmatter
import yaml
from typer.testing import CliRunner

from kb.cli.main import app
from kb.services import brief_service


def test_brief_topics_flow(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    runner = CliRunner()
    runner.invoke(app, ["init"])
    (workspace / "indexes" / "recent.md").write_text("# Recent\n", encoding="utf-8")
    (workspace / "indexes" / "tags.md").write_text("# Tags\n", encoding="utf-8")

    first = runner.invoke(app, ["brief", "topics"])
    first_data = json.loads(first.stdout)

    assert first.exit_code == 0
    assert first_data["status"] == "needs_generation"
    assert first_data["generation_type"] == "brief_topics"
    assert (workspace / first_data["generation_request_path"]).exists()

    result_path = workspace / first_data["generation_result_path"]
    result_path.write_text(
        yaml.safe_dump(
            {
                "request_id": first_data["request_id"],
                "job_id": first_data["job_id"],
                "generation_type": "brief_topics",
                "status": "completed",
                "created_at": "2026-06-22T10:00:00+08:00",
                "sources": [],
                "payload": {
                    "date": first_data["date"],
                    "topics": [
                        {
                            "title": "AI 知识库为什么不该一上来做向量库",
                            "reason": "多条笔记都指向文件化和可追溯优先。",
                            "angle": "从反过度工程切入。",
                            "source_note_ids": ["note_20260618_a"],
                        }
                    ],
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    second = runner.invoke(app, ["brief", "topics", "--continue", first_data["job_id"]])
    second_data = json.loads(second.stdout)
    brief_path = workspace / second_data["brief_path"]

    assert second.exit_code == 0
    assert second_data["status"] == "completed"
    assert brief_path.name == f"topic-picks-{first_data['date'].replace('-', '')}.md"
    assert "AI 知识库为什么不该一上来做向量库" in brief_path.read_text(encoding="utf-8")


def test_brief_weekly_flow(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    runner = CliRunner()
    runner.invoke(app, ["init"])
    (workspace / "indexes" / "recent.md").write_text("# Recent\n", encoding="utf-8")

    first = runner.invoke(app, ["brief", "weekly"])
    first_data = json.loads(first.stdout)

    assert first.exit_code == 0
    assert first_data["status"] == "needs_generation"
    assert first_data["generation_type"] == "brief_weekly"

    result_path = workspace / first_data["generation_result_path"]
    result_path.write_text(
        yaml.safe_dump(
            {
                "request_id": first_data["request_id"],
                "job_id": first_data["job_id"],
                "generation_type": "brief_weekly",
                "status": "completed",
                "created_at": "2026-06-22T10:00:00+08:00",
                "sources": [],
                "payload": {
                    "week": first_data["week"],
                    "new_items": ["AI 知识库架构"],
                    "key_themes": ["AI Native 知识库"],
                    "open_questions": ["是否需要主题页版本记录"],
                    "next_actions": ["整理 AI 知识库主题页"],
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    second = runner.invoke(app, ["brief", "weekly", "--continue", first_data["job_id"]])
    second_data = json.loads(second.stdout)
    brief_path = workspace / second_data["brief_path"]

    assert second.exit_code == 0
    assert second_data["status"] == "completed"
    assert brief_path.name == f"weekly-{first_data['week']}.md"
    assert "AI Native 知识库" in brief_path.read_text(encoding="utf-8")


def test_brief_weekly_continue_rejects_wrong_week(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    runner = CliRunner()
    runner.invoke(app, ["init"])

    first = runner.invoke(app, ["brief", "weekly"])
    first_data = json.loads(first.stdout)
    result_path = workspace / first_data["generation_result_path"]
    result_path.write_text(
        yaml.safe_dump(
            {
                "request_id": first_data["request_id"],
                "job_id": first_data["job_id"],
                "generation_type": "brief_weekly",
                "status": "completed",
                "created_at": "2026-06-22T10:00:00+08:00",
                "sources": [],
                "payload": {
                    "week": "2099-W01",
                    "new_items": [],
                    "key_themes": [],
                    "open_questions": [],
                    "next_actions": [],
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    second = runner.invoke(app, ["brief", "weekly", "--continue", first_data["job_id"]])
    second_data = json.loads(second.stdout)

    assert second.exit_code == 0
    assert second_data["ok"] is False
    assert second_data["error_code"] == "BRIEF_WEEK_MISMATCH"


def test_brief_weekly_only_includes_current_week_sources(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    monkeypatch.setattr(
        brief_service,
        "_now",
        lambda: datetime.fromisoformat("2026-07-16T10:00:00+08:00"),
    )
    runner = CliRunner()
    runner.invoke(app, ["init"])
    note_dir = workspace / "notes" / "20260716"
    note_dir.mkdir(parents=True)
    (note_dir / "current.md").write_text(
        frontmatter.dumps(
            frontmatter.Post("current", created_at="2026-07-15T10:00:00+08:00")
        ),
        encoding="utf-8",
    )
    (note_dir / "old.md").write_text(
        frontmatter.dumps(frontmatter.Post("old", created_at="2026-06-01T10:00:00+08:00")),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["brief", "weekly"])
    data = json.loads(result.stdout)
    request = frontmatter.loads(
        (workspace / data["generation_request_path"]).read_text(encoding="utf-8")
    )

    assert request.metadata["source_paths"] == ["notes/20260716/current.md"]
