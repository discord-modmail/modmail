import base64
import datetime
import glob
import hashlib
import textwrap
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

import click
import requests
import tomli
from click import Context, Option, echo, style
from jinja2 import Template

from .constants import *


__all__ = (
    "NotRequiredIf",
    "get_metadata_from_news",
    "get_project_meta",
    "glob_fragments",
    "err",
    "nonceify",
    "out",
    "render_fragments",
    "save_news_fragment",
    "validate_pull_request_number",
)


def nonceify(body: str) -> str:
    """
    Nonceify the news body!

    Generate hopefully-unique string of characters meant to prevent filename collisions. by computing the
    MD5 hash of the text, converting it to base64 (using the "urlsafe" alphabet), and taking the first
    6 characters of that.
    """
    digest = hashlib.md5(body.encode("utf-8")).digest()  # noqa: S303
    return base64.urlsafe_b64encode(digest)[0:6].decode("ascii")


def _out(message: Optional[str] = None, nl: bool = True, **styles: Any) -> None:
    if message is not None:
        if "bold" not in styles:
            styles["bold"] = True
        message = style(message, **styles)
    echo(message, nl=nl, err=True)


def _err(message: Optional[str] = None, nl: bool = True, **styles: Any) -> None:
    if message is not None:
        if "fg" not in styles:
            styles["fg"] = "red"
        message = style(message, **styles)
    echo(message, nl=nl, err=True)


def out(message: Optional[str] = None, nl: bool = True, **styles: Any) -> None:
    """Utility function to output a styled message to console."""
    _out(message, nl=nl, **styles)


def err(message: Optional[str] = None, nl: bool = True, **styles: Any) -> None:
    """Utility function to output a styled error message to console."""
    _err(message, nl=nl, **styles)


class NotRequiredIf(Option):
    """Custom option class to make option mutually exclusive with another i.e. 'not_required_if'."""

    def __init__(self, *args, **kwargs):
        self.not_required_if = kwargs.pop("not_required_if")
        assert self.not_required_if, "'not_required_if' parameter required"  # noqa: S101
        kwargs["help"] = (
            kwargs.get("help", "")
            + " NOTE: This argument is mutually exclusive with %s" % self.not_required_if
        ).strip()
        super().__init__(*args, **kwargs)

    def handle_parse_result(
        self, ctx: Context, opts: Mapping[str, Any], args: List[str]
    ) -> Tuple[Any, List[str]]:
        """Check if option is mutually exclusive with another, if yes print error and exist."""
        other_present = self.not_required_if in opts

        if other_present:
            we_are_present = self.name in opts
            if we_are_present:
                err(
                    f"{ERROR_MSG_PREFIX} Illegal usage. `%s` is mutually exclusive with `%s`"
                    % (self.name, self.not_required_if),
                    fg="red",
                )
                ctx.exit(code=1)
            else:
                self.prompt = None

        return super().handle_parse_result(ctx, opts, args)


def sanitize_section(section: str) -> str:
    """Cleans up a section string, making it viable as a directory name."""
    return section.replace("/", "-").lower()


def glob_fragments(version: str, sections: Dict[str, str]) -> List[str]:
    """Glob all news fragments present on the repo."""
    filenames = []
    base = os.path.join("news", version)

    if version.lower() != "next":
        wildcard = base + ".md"
        filenames.extend(glob.glob(wildcard))
    else:
        for section in sections:
            wildcard = os.path.join(base, sanitize_section(section), "*.md")
            entries = glob.glob(wildcard)
            entries.sort(reverse=True)
            entries = [x for x in entries if not x.endswith("/README.md")]
            filenames.extend(entries)

    return filenames


def get_metadata_from_news(path: Path) -> dict:
    """Get metadata information from a news entry."""
    new_fragment_file = path.stem
    date, gh_pr, nonce = new_fragment_file.split(".")
    news_type = path.parent.name

    with open(path, "r", encoding="utf-8") as file:
        news_entry = file.read()

    return {
        "date": date,
        "gh_pr": gh_pr,
        "news_type": news_type,
        "nonce": nonce,
        "news_entry": news_entry,
    }


def get_project_meta() -> Tuple[str, str]:
    """Get the project version and name from pyproject.toml file."""
    with open("pyproject.toml", "rb") as pyproject:
        file_contents = tomli.load(pyproject)

    version = file_contents["tool"]["poetry"]["version"]
    name = file_contents["tool"]["poetry"]["name"]
    return name, version


def render_fragments(
    sections: Dict[str, str],
    template: Path,
    metadata: Dict[str, list],
    wrap: bool,
    version_data: Tuple[str, str],
    date: Union[str, datetime.datetime],
) -> str:
    """Render the fragments into a news file."""
    print(template)
    with open(template, mode="r") as template_file:
        jinja_template = Template(template_file.read(), trim_blocks=True)

    version_data = {"name": version_data[0], "version": version_data[1], "date": date}
    res = jinja_template.render(
        sections=sections.copy(),
        version_data=version_data,
        metadata=metadata,
    )

    done = []
    for line in res.split("\n"):
        if wrap:
            done.append(
                textwrap.fill(
                    line,
                    width=79,
                    subsequent_indent=" ",
                    break_long_words=False,
                    break_on_hyphens=False,
                )
            )
        else:
            done.append(line)

    return "\n".join(done).rstrip() + "\n"


def save_news_fragment(ctx: click.Context, gh_pr: int, nonce: str, news_entry: str, news_type: str) -> None:
    """Save received changelog data to a news file."""
    date = datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    path = Path(REPO_ROOT, f"news/next/{news_type}/{date}.pr-{gh_pr}.{nonce}.md")
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

    out(
        f"All done! ✨ 🍰 ✨ Created news fragment at {Path(os.path.relpath(path, start=Path.cwd()))}"
        "\nYou are now ready for commit the changelog!"
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
