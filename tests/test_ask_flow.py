import json

import frontmatter
import yaml
from typer.testing import CliRunner

from kb.cli.main import app


def _write_note(workspace, note_id: str, title: str) -> None:
    path = workspace / "notes" / "20260622" / f"{note_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        frontmatter.dumps(
            frontmatter.Post(
                "## 摘要\n\nLLM Wiki 会持续编译知识。",
                id=note_id,
                title=title,
                tags=["ai", "knowledge", "rag"],
                summary="LLM Wiki 与 RAG 的区别。",
                source_uri=f"https://example.com/{note_id}",
                topic_keys=["ai-knowledge-base"],
            )
        ),
        encoding="utf-8",
    )


def _write_topic(workspace) -> None:
    path = workspace / "wiki" / "topic-ai-knowledge-base.md"
    path.write_text(
        frontmatter.dumps(
            frontmatter.Post(
                "传统 RAG 在查询时重新拼装，LLM Wiki 保存持续更新的综合结果。",
                topic_key="ai-knowledge-base",
                title="AI 知识库与 LLM Wiki",
                source_note_ids=["note_a", "note_b"],
                updated_at="2026-06-22T10:00:00+08:00",
                status="active",
            )
        ),
        encoding="utf-8",
    )


def _write_answer_result(workspace, first_data, question: str, citation_path: str) -> None:
    request = frontmatter.loads(
        (workspace / first_data["generation_request_path"]).read_text(encoding="utf-8")
    )
    (workspace / first_data["generation_result_path"]).write_text(
        yaml.safe_dump(
            {
                "request_id": request.metadata["request_id"],
                "job_id": first_data["job_id"],
                "generation_type": "answer",
                "status": "completed",
                "created_at": "2026-06-22T11:00:00+08:00",
                "sources": [{"path": request.metadata["source_paths"][0]}],
                "payload": {
                    "title": "LLM Wiki 与 RAG",
                    "question": question,
                    "answer_markdown": "LLM Wiki 会保存并持续更新综合结果。",
                    "citations": [{"path": citation_path}],
                    "topic_keys": ["ai-knowledge-base"],
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def test_ask_prefers_wiki_and_does_not_save_by_default(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    runner = CliRunner()
    runner.invoke(app, ["init"])
    _write_note(workspace, "note_a", "LLM Wiki")
    _write_note(workspace, "note_b", "传统 RAG")
    _write_topic(workspace)
    question = "LLM Wiki 和传统 RAG 的区别是什么"

    first = runner.invoke(app, ["ask", question])
    first_data = json.loads(first.stdout)

    assert first_data["status"] == "needs_generation"
    assert first_data["source_paths"][0] == "wiki/topic-ai-knowledge-base.md"
    _write_answer_result(workspace, first_data, question, first_data["source_paths"][0])

    second = runner.invoke(app, ["ask", "--continue", first_data["job_id"]])
    second_data = json.loads(second.stdout)

    assert second_data["status"] == "completed"
    assert second_data["insight_path"] is None
    assert not list((workspace / "wiki").glob("insight-*.md"))


def test_ask_save_writes_insight_and_rejects_unknown_citation(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    runner = CliRunner()
    runner.invoke(app, ["init"])
    _write_note(workspace, "note_a", "LLM Wiki")
    _write_note(workspace, "note_b", "传统 RAG")
    _write_topic(workspace)
    question = "为什么 LLM Wiki 能积累知识"

    first = runner.invoke(app, ["ask", question, "--save"])
    first_data = json.loads(first.stdout)
    _write_answer_result(workspace, first_data, question, "raw/not-allowed.md")
    rejected = runner.invoke(app, ["ask", "--continue", first_data["job_id"]])
    rejected_data = json.loads(rejected.stdout)

    assert rejected_data["error_code"] == "ANSWER_CITATION_INVALID"

    _write_answer_result(workspace, first_data, question, first_data["source_paths"][0])
    completed = runner.invoke(app, ["ask", "--continue", first_data["job_id"]])
    completed_data = json.loads(completed.stdout)

    assert completed_data["status"] == "completed"
    assert (workspace / completed_data["insight_path"]).exists()
    assert (workspace / "indexes" / "insights.md").exists()
    assert "ask | LLM Wiki 与 RAG" in (workspace / "logs" / "history.md").read_text(
        encoding="utf-8"
    )
