from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

import click

from . import __version__
from .constants import *
from .utils import *


@click.group(context_settings=dict(help_option_names=["-h", "--help"]), invoke_without_command=True)
@click.version_option(version=__version__)
@click.pass_context
def cli_main(ctx: click.Context) -> None:
    """
    Modmail News 📜🤖.

    As part of discord-modmail’s workflow, any non-trivial change to the codebase
    requires an accompanying news/ file in the pull request. This submodule helps
    contributors and maintainers to work with news files (changelogs) by automating
    the process of generating, compiling and validating them!
    """
    if not ctx.args and not ctx.resilient_parsing and not ctx.command:
        click.echo(ctx.get_help())
        ctx.exit()


@cli_main.command("add")
@click.option(
    "-e",
    "--editor",
    cls=NotRequiredIf,
    not_required_if="message",
    type=str,
)
@click.option(
    "-m",
    "--message",
    cls=NotRequiredIf,
    not_required_if="editor",
)
@click.option(
    "-t",
    "--type",
    type=click.Choice([section.lower() for section in SECTIONS]),
    prompt=True,
)
@click.option(
    "--pr",
    type=int,
    prompt=True,
    callback=validate_pull_request_number,
)
@click.pass_context
def cli_add_news(ctx: click.Context, message: str, editor: str, type: str, pr: int) -> None:
    """Add a news entry 📜 to the current discord-modmail repo for your awesome change!"""
    if not message:
        message_notes = []
        while True:
            content = click.edit(
                "\n".join((TEMPLATE, *message_notes)),
                editor=editor,
                extension="md",
            )

            if not content:
                message_notes = ["# ERROR: No content found previously"]
                continue

            message = "\n".join(
                line.rstrip() for line in content.split("\n") if not line.lstrip().startswith("#")
            )

            if message is None:
                out("Aborting creating a new news fragment!", fg="yellow")
                ctx.exit(1)

            break

    save_news_fragment(ctx, pr, message, type)


@cli_main.command("build")
@click.option(
    "--edit/--no-edit",
    default=None,
    help="Open the changelog file in your text editor.",
)
@click.option("--keep", is_flag=True, help="Keep the fragment files that are collected.")
@click.pass_context
def cli_build_news(ctx: click.Context, edit: Optional[bool], keep: bool) -> None:
    """Build a combined news file 📜 from news fragments."""
    filenames = glob_fragments("next", SECTIONS)
    _file_metadata = {}
    file_metadata = defaultdict(list)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not filenames:
        err("No news fragments found. Exiting")
        ctx.exit()
    else:
        for filename in filenames:
            if not filename.endswith(".md"):
                continue
            _file_metadata[filename] = get_metadata_from_news(Path(filename))

    # Group metadata according to news_type
    for path, fragment in _file_metadata.items():
        news_type = fragment["news_type"]
        del fragment["news_type"]
        fragment["path"] = path
        file_metadata[news_type].append(fragment)

    name, version = get_project_meta()
    version_news = render_fragments(
        sections=SECTIONS,
        template=TEMPLATE_FILE_PATH,
        metadata=file_metadata,
        wrap=True,
        version_data=(name, version),
        date=date,
    )
    news_path = Path(REPO_ROOT, f"news/{version}.md")

    with open(news_path, mode="w") as file:
        file.write(version_news)

    out(f"All done! ✨ 🍰 ✨ Created {name}-v{version} news at {news_path}")

    if edit:
        click.edit(filename=str(news_path))

    if not keep:
        for news_fragment in NEWS_NEXT.glob("*/*.md"):
            os.remove(news_fragment)
        out("🍰 Cleared existing `news/next` news fragments!")


if __name__ == "__main__":
    cli_main()
