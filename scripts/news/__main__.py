import os
from pathlib import Path
from typing import Optional

import click
import requests

from scripts.news.utils import NotRequiredIf, err, nonceify, out

from . import ERROR_MSG_PREFIX, __version__


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


class NewsFragment:
    def __init__(self, ctx: click.Context, gh_pr: int, nonce: str, news_entry: str, _type: str) -> None:
        self.ctx = ctx
        self.gh_pr = gh_pr
        self.nonce = nonce
        self.news_entry = news_entry
        self.news_type = _type

    def save_file(self) -> None:
        """Save received changelog data to a news file."""
        path = Path(Path.cwd(), f"news/next/pr-{self.gh_pr}.{self.news_type}.{self.nonce}.md")
        if not path.parent.exists():
            err(
                f"{ERROR_MSG_PREFIX} `news/next/` doesn't exist.\nYou are either in the wrong directory while "
                "running this command (should be in the project root) or the path doesn't exist, if it "
                "doesn't exist please create it and run this command again :) Happy change-logging!",
                fg="blue",
            )
            self.ctx.exit(1)
        elif path.exists():
            # The file exists
            err(f"{ERROR_MSG_PREFIX} {Path(os.path.relpath(path, start=Path.cwd()))} already exists")
            self.ctx.exit(1)

        text = str(self.news_entry)
        with open(path, "wt", encoding="utf-8") as file:
            file.write(text)

        out(f"All done! ✨ 🍰 ✨ Created news fragment at {Path(os.path.relpath(path, start=Path.cwd()))}")


def validate_pull_request_number(
    ctx: click.Context, param: click.Parameter, value: Optional[int]
) -> Optional[int]:
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


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option("-v", "--verbose", is_flag=True, help="Enables verbose mode")
@click.version_option(version=__version__)
@click.pass_context
def cli_main(ctx: click.Context, verbose: bool) -> None:
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
    type=click.Choice(["feature", "bug", "maintenance"]),
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
    """Add a changelog 📜 (news/ entry) to the current discord-modmail repo for your awesome change!"""
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
                message_notes = "# ERROR: No content found previously"
                continue

            message = "\n".join(
                [line.rstrip() for line in content.split("\n") if not line.lstrip().startswith("#")]
            )

            if message is None:
                out("Aborting creating new news fragment/changelog!", fg="yellow")
                ctx.exit(1)

            break

    news_fragment = NewsFragment(ctx, pr_number, nonceify(message), message, type)
    news_fragment.save_file()


if __name__ == "__main__":
    cli_main()
