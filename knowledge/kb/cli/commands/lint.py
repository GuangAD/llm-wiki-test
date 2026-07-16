import json
from pathlib import Path

import typer

from kb.services.lint_service import continue_lint, request_lint

app = typer.Typer()


@app.callback(invoke_without_command=True)
def lint(
    continue_job: str | None = typer.Option(None, "--continue", "--continue-job"),
) -> None:
    response = continue_lint(Path.cwd(), continue_job) if continue_job else request_lint(Path.cwd())
    typer.echo(json.dumps(response, ensure_ascii=False, separators=(",", ":")))
