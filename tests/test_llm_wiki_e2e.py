import json

import frontmatter
import yaml
from typer.testing import CliRunner

from kb.cli.main import app


def _write_result(workspace, request_path: str, result_data: dict) -> None:
    request = frontmatter.loads((workspace / request_path).read_text(encoding="utf-8"))
    result_data["request_id"] = request.metadata["request_id"]
    result_data["job_id"] = request.metadata["job_id"]
    result_data["generation_type"] = request.metadata["generation_type"]
    result_data["status"] = "completed"
    result_data["created_at"] = "2026-07-16T10:00:00+08:00"
    result_data["sources"] = [
        {"path": path} for path in request.metadata.get("source_paths", [])
    ]
    (workspace / request.metadata["result_path"]).write_text(
        yaml.safe_dump(result_data, allow_unicode=True),
        encoding="utf-8",
    )


def _ingest(runner, workspace, text: str, title: str) -> dict:
    first = json.loads(runner.invoke(app, ["ingest", text]).stdout)
    _write_result(
        workspace,
        first["generation_request_path"],
        {
            "content_id": first["content_id"],
            "payload": {
                "title": title,
                "summary": "LLM Wiki 会持续编译个人知识。",
                "tags": ["ai", "knowledge", "workflow"],
                "stance": "approve",
                "key_points": ["保存原文", "形成笔记", "编译主题"],
                "my_judgement": "适合作为个人知识库架构。",
                "useful_for": ["写作", "研究"],
                "related_topics": ["ai-knowledge-base"],
            },
        },
    )
    return json.loads(runner.invoke(app, ["ingest", "--continue", first["job_id"]]).stdout)


def test_complete_llm_wiki_loop(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    runner = CliRunner()
    runner.invoke(app, ["init"])

    _ingest(runner, workspace, "LLM Wiki source one", "LLM Wiki 原理")
    second = _ingest(runner, workspace, "LLM Wiki source two", "知识编译流程")
    topic_request_path = second["topic_request_paths"][0]
    _write_result(
        workspace,
        topic_request_path,
        {
            "payload": {
                "topic_key": "ai-knowledge-base",
                "title": "AI 知识库",
                "definition": "把原始资料持续编译为可复用知识。",
                "conclusions": ["Wiki 应成为查询入口。"],
                "disagreements": ["何时需要向量检索仍需观察。"],
                "extensions": ["增加知识健康检查。"],
                "source_note_ids": [
                    path.stem for path in sorted((workspace / "notes").glob("**/*.md"))
                ],
            }
        },
    )
    topic_request = frontmatter.loads((workspace / topic_request_path).read_text(encoding="utf-8"))
    topic_job_id = topic_request.metadata["job_id"]
    topic = json.loads(
        runner.invoke(
            app,
            ["compile", "--continue", topic_job_id, "--topic-key", "ai-knowledge-base"],
        ).stdout
    )
    assert topic["status"] == "completed"

    question = "LLM Wiki 为什么能够积累知识"
    ask = json.loads(runner.invoke(app, ["ask", "--save", question]).stdout)
    _write_result(
        workspace,
        ask["generation_request_path"],
        {
            "payload": {
                "title": "LLM Wiki 的复利原理",
                "question": question,
                "answer_markdown": "它把综合结果持久化，并在后续查询中复用。",
                "citations": [{"path": ask["source_paths"][0]}],
                "topic_keys": ["ai-knowledge-base"],
            }
        },
    )
    answer = json.loads(runner.invoke(app, ["ask", "--continue", ask["job_id"]]).stdout)
    assert answer["insight_path"]

    lint = json.loads(runner.invoke(app, ["lint"]).stdout)
    _write_result(
        workspace,
        lint["generation_request_path"],
        {"payload": {"summary": "知识库结构正常。", "issues": []}},
    )
    lint_result = json.loads(
        runner.invoke(app, ["lint", "--continue", lint["job_id"]]).stdout
    )
    assert lint_result["report_path"]

    topics = json.loads(runner.invoke(app, ["brief", "topics"]).stdout)
    _write_result(
        workspace,
        topics["generation_request_path"],
        {
            "payload": {
                "date": topics["date"],
                "topics": [
                    {
                        "title": "为什么知识库需要先编译",
                        "reason": "已有多条来源形成共同结论。",
                        "angle": "对比传统 RAG。",
                        "source_note_ids": [
                            path.stem
                            for path in sorted((workspace / "notes").glob("**/*.md"))
                        ],
                    }
                ],
            }
        },
    )
    assert json.loads(
        runner.invoke(app, ["brief", "topics", "--continue", topics["job_id"]]).stdout
    )["brief_path"]

    weekly = json.loads(runner.invoke(app, ["brief", "weekly"]).stdout)
    _write_result(
        workspace,
        weekly["generation_request_path"],
        {
            "payload": {
                "week": weekly["week"],
                "new_items": ["新增两条知识库资料"],
                "key_themes": ["LLM Wiki"],
                "open_questions": ["何时引入混合检索"],
                "next_actions": ["继续积累同主题来源"],
            }
        },
    )
    assert json.loads(
        runner.invoke(app, ["brief", "weekly", "--continue", weekly["job_id"]]).stdout
    )["brief_path"]

    status = json.loads(runner.invoke(app, ["status"]).stdout)
    assert status["counts"] == {
        "raw": 2,
        "notes": 2,
        "wiki": 2,
        "topics": 1,
        "insights": 1,
        "briefs": 2,
        "reports": 1,
    }
    history = (workspace / "logs" / "history.md").read_text(encoding="utf-8")
    for event in ["ingest", "compile", "ask", "lint", "brief"]:
        assert f"] {event} |" in history
