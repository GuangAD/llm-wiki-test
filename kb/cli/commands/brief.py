import json
from pathlib import Path

import typer

from kb.services.brief_service import (
    continue_brief_topics,
    continue_brief_weekly,
    request_brief_topics,
    request_brief_weekly,
)

app = typer.Typer()


@app.command()
def topics(
    continue_job: str | None = typer.Option(None, "--continue", "--continue-job"),
) -> None:
    if continue_job:
        response = continue_brief_topics(Path.cwd(), continue_job)
    else:
        response = request_brief_topics(Path.cwd())
    typer.echo(json.dumps(response, ensure_ascii=False, separators=(",", ":")))


@app.command()
def weekly(
    continue_job: str | None = typer.Option(None, "--continue", "--continue-job"),
) -> None:
    if continue_job:
        response = continue_brief_weekly(Path.cwd(), continue_job)
    else:
        response = request_brief_weekly(Path.cwd())
    typer.echo(json.dumps(response, ensure_ascii=False, separators=(",", ":")))
