import typer

from modmail_cli import docs

app = typer.Typer()
app.add_typer(docs.app, name="docs")

if __name__ == "__main__":
    app()
