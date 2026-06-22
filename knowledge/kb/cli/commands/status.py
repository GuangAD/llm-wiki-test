import json
from pathlib import Path

import typer

from kb.services.status_service import status as status_service

app = typer.Typer()


@app.callback(invoke_without_command=True)
def status() -> None:
    response = status_service(Path.cwd())
    typer.echo(json.dumps(response, ensure_ascii=False, separators=(",", ":")))
