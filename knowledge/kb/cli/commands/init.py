import json
from pathlib import Path

import typer

from kb.core.atomic import atomic_write_text

app = typer.Typer()

RUNTIME_DIRS = [
    "raw",
    "notes",
    "wiki",
    "briefs",
    "indexes",
    "prompts",
    "state/jobs",
    "state/generation_requests",
    "state/generation_results",
    "state/locks",
    "logs",
    "reports",
]

NOTE_PROMPT = """请根据原文生成结构化 note，并写入 GenerationRequest 中的 result_path。

输出必须是 YAML，字段必须符合 note_v1 schema。
"""

TOPIC_PROMPT = """请根据来源 note 生成结构化主题页结果，并写入 GenerationRequest 中的 result_path。

输出必须是 YAML，字段必须符合 topic_v1 schema。
"""

BRIEF_TOPICS_PROMPT = """请根据知识库索引和来源内容生成结构化选题结果，并写入 GenerationRequest 中的 result_path。

输出必须是 YAML，字段必须符合 brief_topics_v1 schema。
"""

BRIEF_WEEKLY_PROMPT = """请根据本周知识库新增内容生成结构化周报结果，并写入 GenerationRequest 中的 result_path。

输出必须是 YAML，字段必须符合 brief_weekly_v1 schema。
"""

ANSWER_PROMPT = """请根据 GenerationRequest 的问题和 source_paths 生成结构化回答。

只允许引用 source_paths 中的文件。输出必须是 YAML，字段必须符合 answer_v1 schema。
"""

LINT_PROMPT = """请根据确定性检查结果和 source_paths 检查知识库的语义健康度。

只生成报告，不直接修改知识文件。输出必须是 YAML，字段必须符合 lint_v1 schema。
"""

PROMPTS = {
    "note.md": NOTE_PROMPT,
    "topic.md": TOPIC_PROMPT,
    "brief-topics.md": BRIEF_TOPICS_PROMPT,
    "brief-weekly.md": BRIEF_WEEKLY_PROMPT,
    "answer.md": ANSWER_PROMPT,
    "lint.md": LINT_PROMPT,
}


@app.callback(invoke_without_command=True)
def init() -> None:
    root = Path.cwd()
    for path in RUNTIME_DIRS:
        (root / path).mkdir(parents=True, exist_ok=True)
    for filename, content in PROMPTS.items():
        prompt_path = root / "prompts" / filename
        if not prompt_path.exists():
            atomic_write_text(prompt_path, content)
    history_path = root / "logs" / "history.md"
    if not history_path.exists():
        atomic_write_text(history_path, "# Knowledge History\n")
    typer.echo(
        json.dumps(
            {
                "ok": True,
                "command": "kb init",
                "status": "completed",
                "next_action": "none",
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
