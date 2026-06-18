import json
from pathlib import Path

import typer

from kb.core.atomic import atomic_write_text

app = typer.Typer()

RUNTIME_DIRS = [
    "raw",
    "notes",
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


@app.callback(invoke_without_command=True)
def init() -> None:
    root = Path.cwd()
    for path in RUNTIME_DIRS:
        (root / path).mkdir(parents=True, exist_ok=True)
    prompt_path = root / "prompts" / "note.md"
    if not prompt_path.exists():
        atomic_write_text(prompt_path, NOTE_PROMPT)
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
