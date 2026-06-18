import json
from pathlib import Path

import typer

from kb.core.errors import error_response
from kb.services.ingest_service import ingest_continue, ingest_first_pass

app = typer.Typer()


@app.callback(invoke_without_command=True)
def ingest(
    input_value: str | None = typer.Argument(None),
    continue_job: str | None = typer.Option(None, "--continue", "--continue-job"),
) -> None:
    if continue_job:
        response = ingest_continue(Path.cwd(), continue_job)
    elif input_value:
        response = ingest_first_pass(Path.cwd(), input_value)
    else:
        response = error_response(
            command="kb ingest",
            status="permanent_failed",
            error_code="INVALID_INPUT",
            error_message="input_value or --continue is required.",
            retryable=False,
            next_action="none",
        )
    typer.echo(json.dumps(response, ensure_ascii=False, separators=(",", ":")))
