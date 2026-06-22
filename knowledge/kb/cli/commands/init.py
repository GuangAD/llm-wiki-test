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

PROMPTS = {
    "note.md": NOTE_PROMPT,
    "topic.md": TOPIC_PROMPT,
    "brief-topics.md": BRIEF_TOPICS_PROMPT,
    "brief-weekly.md": BRIEF_WEEKLY_PROMPT,
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
