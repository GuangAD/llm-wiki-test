import json
from pathlib import Path

import typer

from kb.services.ask_service import ask as ask_service

app = typer.Typer()


@app.callback(invoke_without_command=True)
def ask(question: str = typer.Argument(...)) -> None:
    response = ask_service(Path.cwd(), question)
    typer.echo(json.dumps(response, ensure_ascii=False, separators=(",", ":")))
