import typer

from kb.cli.commands import ask, brief, compile, ingest, init, status

app = typer.Typer(no_args_is_help=True)
app.add_typer(init.app, name="init")
app.add_typer(ingest.app, name="ingest")
app.add_typer(ask.app, name="ask")
app.add_typer(compile.app, name="compile")
app.add_typer(brief.app, name="brief")
app.add_typer(status.app, name="status")


@app.callback()
def main() -> None:
    """Local AI knowledge base CLI."""
