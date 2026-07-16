import json
from pathlib import Path

import typer

from kb.core.errors import error_response
from kb.services.ask_service import continue_answer, request_answer

app = typer.Typer(context_settings={"allow_interspersed_args": True})


@app.callback(invoke_without_command=True)
def ask(
    question: str | None = typer.Argument(None),
    continue_job: str | None = typer.Option(None, "--continue", "--continue-job"),
    save: bool = typer.Option(False, "--save"),
) -> None:
    if continue_job:
        response = continue_answer(Path.cwd(), continue_job)
    elif question:
        response = request_answer(Path.cwd(), question, save)
    else:
        response = error_response(
            command="kb ask",
            status="permanent_failed",
            error_code="INVALID_INPUT",
            error_message="question or --continue is required.",
            retryable=False,
            next_action="none",
        )
    typer.echo(json.dumps(response, ensure_ascii=False, separators=(",", ":")))
