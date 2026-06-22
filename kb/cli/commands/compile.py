import json
from pathlib import Path

import typer

from kb.core.errors import error_response
from kb.services.topic_service import compile_continue

app = typer.Typer()


@app.callback(invoke_without_command=True)
def compile_command(
    continue_job: str | None = typer.Option(None, "--continue", "--continue-job"),
    topic_key: str | None = typer.Option(None, "--topic-key"),
) -> None:
    if continue_job and topic_key:
        response = compile_continue(Path.cwd(), continue_job, topic_key)
    else:
        response = error_response(
            command="kb compile",
            status="permanent_failed",
            error_code="INVALID_INPUT",
            error_message="--continue and --topic-key are required.",
            retryable=False,
            next_action="none",
        )
    typer.echo(json.dumps(response, ensure_ascii=False, separators=(",", ":")))
