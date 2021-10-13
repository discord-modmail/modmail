import atexit
import os
import shlex
import shutil
import subprocess
import tempfile

import click

from scripts.news.utils import NotRequiredIf, err, find_editor

from . import __version__


TEMPLATE = """

# Write your news/ (changelog) entry below. It should be a simple Markdown paragraph.
#####################################################################################
""".lstrip()


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option("-v", "--verbose", is_flag=True, help="Enables verbose mode")
@click.version_option(version=__version__)
@click.pass_context
def cli_main(ctx: click.Context, verbose: bool) -> None:
    """
    Modmail News 📜🤖

    As part of discord-modmail’s workflow, any non-trivial change to the codebase
    requires an accompanying news/ file in the pull request. This submodule helps
    contributors and maintainers to work with news files (changelogs) by automating
    the process of generating, compiling and validating them!
    """
    ...


@cli_main.command("add")
@click.option(
    "-e",
    "--editor",
    default=find_editor(),
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
    type=click.Choice(["feature", "bug", "maintenance"]),
    prompt=True,
)
@click.pass_context
def cli_add_news(ctx: click.Context, message: str, editor: str, type: str) -> None:
    """Add a changelog 📜 (news/ entry) to the current discord-modmail repo for your awesome change!"""
    handle, tmp_path = tempfile.mkstemp(".md")
    os.close(handle)
    atexit.register(lambda: os.unlink(tmp_path))

    def init_tmp_with_template():
        with open(tmp_path, "wt", encoding="utf-8") as file:
            file.write(TEMPLATE)

    init_tmp_with_template()

    # We need to be clever about EDITOR.
    # On the one hand, it might be a legitimate path to an
    #   executable containing spaces.
    # On the other hand, it might be a partial command-line
    #   with options.
    if shutil.which(editor):
        args = [editor]
    else:
        args = list(shlex.split(editor))
        if not shutil.which(args[0]):
            err(
                f"Invalid --editor value: `{editor}`.\nIf you didn't supply it was taken from "
                f"either '$GIT_EDITOR', '$EDITOR' (environment variables)"
            )
            ctx.exit(1)

    args.append(tmp_path)
    subprocess.run(args)
    with open(tmp_path, "rt", encoding="utf-8") as file:
        text = file.read()

    print(text)


if __name__ == "__main__":
    cli_main()
