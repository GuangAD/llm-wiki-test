import json

import frontmatter
import yaml
from typer.testing import CliRunner

from kb.cli.main import app


def test_compile_continue_writes_topic_page_and_index(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    runner = CliRunner()
    runner.invoke(app, ["init"])
    result_path = workspace / "state" / "generation_results" / "job_topic-topic.yaml"
    result_path.write_text(
        yaml.safe_dump(
            {
                "request_id": "gen_topic",
                "job_id": "job_topic",
                "generation_type": "topic",
                "status": "completed",
                "created_at": "2026-06-22T10:00:00+08:00",
                "sources": [
                    {"path": "notes/20260618/note_20260618_a.md"},
                    {"path": "notes/20260618/note_20260618_b.md"},
                ],
                "payload": {
                    "topic_key": "ai-knowledge-base",
                    "title": "AI 知识库",
                    "definition": "讨论个人 AI 知识库的边界和实现。",
                    "conclusions": ["文件优先比一开始上向量库更稳。"],
                    "disagreements": ["是否需要主题页版本记录仍未确定。"],
                    "extensions": ["补充选题生成链路。"],
                    "source_note_ids": ["note_20260618_a", "note_20260618_b"],
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["compile", "--continue", "job_topic", "--topic-key", "ai-knowledge-base"],
    )
    data = json.loads(result.stdout)
    topic_path = workspace / "wiki" / "topic-ai-knowledge-base.md"
    topic = frontmatter.loads(topic_path.read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert data["status"] == "completed"
    assert data["topic_path"] == "wiki/topic-ai-knowledge-base.md"
    assert topic.metadata["topic_key"] == "ai-knowledge-base"
    assert "文件优先比一开始上向量库更稳。" in topic.content
    assert "- [AI 知识库](../wiki/topic-ai-knowledge-base.md)" in (
        workspace / "indexes" / "topics.md"
    ).read_text(encoding="utf-8")


def test_compile_continue_rejects_mismatched_topic_key(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    runner = CliRunner()
    runner.invoke(app, ["init"])
    result_path = workspace / "state" / "generation_results" / "job_topic-topic.yaml"
    result_path.write_text(
        yaml.safe_dump(
            {
                "request_id": "gen_topic",
                "job_id": "job_topic",
                "generation_type": "topic",
                "status": "completed",
                "created_at": "2026-06-22T10:00:00+08:00",
                "sources": [{"path": "notes/20260618/note_20260618_a.md"}],
                "payload": {
                    "topic_key": "ai-knowledge-base",
                    "title": "AI 知识库",
                    "definition": "讨论个人 AI 知识库的边界和实现。",
                    "conclusions": ["结论"],
                    "disagreements": [],
                    "extensions": [],
                    "source_note_ids": ["note_20260618_a", "note_20260618_b"],
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["compile", "--continue", "job_topic", "--topic-key", "other-topic"],
    )
    data = json.loads(result.stdout)

    assert result.exit_code == 0
    assert data["ok"] is False
    assert data["error_code"] == "TOPIC_KEY_MISMATCH"
