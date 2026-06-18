import typer

from kb.cli.commands import ask, ingest, init

app = typer.Typer(no_args_is_help=True)
app.add_typer(init.app, name="init")
app.add_typer(ingest.app, name="ingest")
app.add_typer(ask.app, name="ask")


@app.callback()
def main() -> None:
    """Local AI knowledge base CLI."""
