import json

import yaml
from typer.testing import CliRunner

from kb.cli.main import app


def test_ingest_text_creates_generation_request(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    runner = CliRunner()
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["ingest", "AI 会改变个人知识管理"])
    data = json.loads(result.stdout)

    assert result.exit_code == 0
    assert data["status"] == "needs_generation"
    assert (workspace / "state" / "generation_requests").exists()
    assert list((workspace / "state" / "generation_requests").glob("*.md"))


def test_ingest_continue_writes_note_and_indexes(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    runner = CliRunner()
    runner.invoke(app, ["init"])
    first = runner.invoke(app, ["ingest", "AI 会改变个人知识管理"])
    data = json.loads(first.stdout)
    result_path = workspace / data["generation_result_path"]
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        yaml.safe_dump(
            {
                "request_id": "gen_20260618143022_a8f31c92_note",
                "job_id": data["job_id"],
                "content_id": data["content_id"],
                "generation_type": "note",
                "status": "completed",
                "created_at": "2026-06-18T14:32:00+08:00",
                "sources": [{"path": "raw/20260618/example.md", "source_uri": "text:test"}],
                "payload": {
                    "title": "AI 知识管理",
                    "summary": "AI 能提升个人知识管理效率。",
                    "tags": ["ai", "knowledge", "workflow"],
                    "stance": "approve",
                    "key_points": ["更快整理", "更容易检索", "更适合写作"],
                    "my_judgement": "值得纳入知识库。",
                    "useful_for": ["写作", "选题"],
                    "related_topics": ["ai-knowledge-base"],
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    second = runner.invoke(app, ["ingest", "--continue", data["job_id"]])
    second_data = json.loads(second.stdout)

    assert second.exit_code == 0
    assert second_data["status"] == "completed"
    assert list((workspace / "notes").glob("**/*.md"))
    assert (workspace / "indexes" / "recent.md").exists()


def test_ingest_continue_compatibility_alias(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    runner = CliRunner()
    runner.invoke(app, ["init"])
    first = runner.invoke(app, ["ingest", "AI 会改变写作流程"])
    data = json.loads(first.stdout)

    second = runner.invoke(app, ["ingest", "--continue-job", data["job_id"]])
    second_data = json.loads(second.stdout)

    assert second.exit_code == 0
    assert second_data["error_code"] == "GENERATION_RESULT_NOT_FOUND"
    assert second_data["next_action"] == "write_generation_result"
