import os
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click
import requests

from . import ERROR_MSG_PREFIX, __version__
from .utils import (
    NotRequiredIf,
    err,
    get_metadata_from_file,
    get_project_meta,
    glob_fragments,
    load_toml_config,
    nonceify,
    out,
    render_fragments,
)


PR_ENDPOINT = "https://api.github.com/repos/discord-modmail/modmail/pulls/{number}"
BAD_RESPONSE = {
    404: "Pull request not located! Please enter a valid number!",
    403: "Rate limit has been hit! Please try again later!",
}

TEMPLATE = """
# Please write your news content. When finished, save the file.
# In order to abort, exit without saving.
# Lines starting with \"#\" are ignored.

""".lstrip()
NO_NEWS_PATH_ERROR = (
    f"{ERROR_MSG_PREFIX} `news/next/` doesn't exist.\nYou are either in the wrong directory while"
    " running this command (should be in the project root) or the path doesn't exist, if it "
    "doesn't exist please create it and run this command again :) Happy change-logging!"
)

CONFIG = load_toml_config()
SECTIONS = [_type for _type, _ in CONFIG.get("types").items()]


def save_news_fragment(ctx: click.Context, gh_pr: int, nonce: str, news_entry: str, news_type: str) -> None:
    """Save received changelog data to a news file."""
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = Path(Path.cwd(), f"news/next/{news_type}/{date}.pr-{gh_pr}.{nonce}.md")
    if not path.parents[1].exists():
        err(NO_NEWS_PATH_ERROR, fg="blue")
        ctx.exit(1)
    elif not path.parents[0].exists():
        make_news_type_dir = click.confirm(
            f"Should I make the new type DIR for the news type at {path.parents[0]}"
        )
        if make_news_type_dir:
            path.parents[0].mkdir(exist_ok=True)
    elif path.exists():
        # The file exists
        err(f"{ERROR_MSG_PREFIX} {Path(os.path.relpath(path, start=Path.cwd()))} already exists")
        ctx.exit(1)

    text = str(news_entry)
    with open(path, "wt", encoding="utf-8") as file:
        file.write(text)

    # Add news fragment to git stage
    subprocess.run(["git", "add", "--force", path]).check_returncode()

    out(
        f"All done! ✨ 🍰 ✨ Created news fragment at {Path(os.path.relpath(path, start=Path.cwd()))}"
        "\nYou are now ready for commit!"
    )


def validate_pull_request_number(
    ctx: click.Context, _param: click.Parameter, value: Optional[int]
) -> Optional[int]:
    """Check if the given pull request number exists on the github repository."""
    r = requests.get(PR_ENDPOINT.format(number=value))
    if r.status_code == 403:
        if r.headers.get("X-RateLimit-Remaining") == "0":
            err(f"{ERROR_MSG_PREFIX} Ratelimit reached, please retry in a few minutes.")
            ctx.exit()
        err(f"{ERROR_MSG_PREFIX} Cannot access pull request.")
        ctx.exit()
    elif r.status_code in (404, 410):
        err(f"{ERROR_MSG_PREFIX} PR not found.")
        ctx.exit()
    elif r.status_code != 200:
        err(f"{ERROR_MSG_PREFIX} Error while fetching issue, retry again after sometime.")
        ctx.exit()

    return value


@click.group(context_settings=dict(help_option_names=["-h", "--help"]), invoke_without_command=True)
@click.version_option(version=__version__)
def cli_main() -> None:
    """
    Modmail News 📜🤖.

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
    "--pr-number",
    type=int,
    prompt=True,
    callback=validate_pull_request_number,
)
@click.pass_context
def cli_add_news(ctx: click.Context, message: str, editor: str, type: str, pr_number: int) -> None:
    """Add a news entry 📜 to the current discord-modmail repo for your awesome change!"""
    if not message:
        message_notes = []
        while True:
            content = click.edit(
                (
                    "# Please write your news content. When finished, save the file.\n"
                    "# In order to abort, exit without saving.\n"
                    "# Lines starting with '#' are ignored.\n"
                    "\n".join(message_notes)
                ),
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

    save_news_fragment(ctx, pr_number, nonceify(message), message, type)


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
            _file_metadata[filename] = get_metadata_from_file(Path(filename))

    # Group metadata according to news_type
    for path, fragment in _file_metadata.items():
        news_type = fragment["news_type"]
        del fragment["news_type"]
        fragment["path"] = path
        file_metadata[news_type].append(fragment)

    template = CONFIG["core"].get("template")
    if not template:
        template = Path(Path.cwd(), "scripts/news/template.md.jinja")
    else:
        template = Path(Path.cwd(), f"scripts/news/{template}")

    if not template.exists():
        err(
            f"{ERROR_MSG_PREFIX} Template at {template.relative_to(Path.cwd())} not found :(. Make sure "
            f"your path is relative to `scripts/news`!"
        )

    name, version = get_project_meta()
    version_news = render_fragments(
        section_names=CONFIG["types"],
        template=template,
        metadata=file_metadata,
        wrap=True,
        version_data=(name, version),
        date=date,
    )
    news_path = Path(Path.cwd(), f"news/{version}.md")

    with open(news_path, mode="w") as file:
        file.write(version_news)

    out(f"All done! ✨ 🍰 ✨ Created {name}-v{version} news at {news_path}")

    if edit:
        click.edit(filename=str(news_path))

    if not keep:
        files = Path(Path.cwd(), "scripts/news/next")
        for news_fragment in files.glob("*.md"):
            os.remove(news_fragment)
        out("🍰 Cleared existing `scripts/news/next` news fragments!")


if __name__ == "__main__":
    cli_main()
