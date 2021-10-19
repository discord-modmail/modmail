import enum
import pathlib
import re

import click
import requests

from ..utils import load_toml_config


NEWS_NEXT_DIR = "news/next/"
SKIP_NEWS_LABEL = "skip changelog"
GH_API_URL = "https://api.github.com/"
HEADERS = {"accept": "application/vnd.github.v3+json"}

CONFIG = load_toml_config()
SECTIONS = [_type for _type, _ in CONFIG.get("types").items()]

FILENAME_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}(?:-\d{2}-\d{2}-\d{2})?\."  # match `yyyy-mm-dd` or `yyyy-m-d`
    r"pr-\d+(?:,\d+)*\."  # Issue number(s)
    fr"({'|'.join(SECTIONS)})\."  # Section type
    r"[A-Za-z0-9_=-]+\."  # Nonce (URL-safe base64)
    r"md",  # File extension"""
    re.VERBOSE,
)


class StatusState(enum.Enum):
    """Status state for the changelog checking."""

    SUCCESS = "success"
    ERROR = "error"
    FAILURE = "failure"


def is_news_dir(filename: str) -> bool:
    """Return True if file is in the News directory."""
    return filename.startswith(NEWS_NEXT_DIR)


@click.command()
@click.argument("pr", nargs=1, type=int)
def main(pr: int) -> None:
    """Main function to check for a changelog entry."""
    r = requests.get(f"{GH_API_URL}repos/discord-modmail/modmail/pulls/{pr}/files", headers=HEADERS)
    files_changed = r.json()
    in_next_dir = file_found = False
    status = None

    for file in files_changed:
        if not is_news_dir(file["filename"]):
            continue
        in_next_dir = True
        file_path = pathlib.PurePath(file["filename"])
        if len(file_path.parts) != 4:  # news, next, <type>, <entry>
            continue
        file_found = True
        if FILENAME_RE.match(file_path.name) and len(file["patch"]) >= 1:
            status = (f"News entry found in {NEWS_NEXT_DIR}", StatusState.SUCCESS)
            break
    else:
        _r = requests.get(f"{GH_API_URL}repos/discord-modmail/modmail/pulls/{pr}", headers=HEADERS)
        pr_data = _r.json()
        labels = [label["name"] for label in pr_data["labels"]]
        if SKIP_NEWS_LABEL in labels:
            description = f"'{SKIP_NEWS_LABEL}' label found"
        else:
            if not in_next_dir:
                description = f'No news entry in {NEWS_NEXT_DIR} or "{SKIP_NEWS_LABEL}" label found'
            elif not file_found:
                description = "News entry not in an appropriate directory"
            else:
                description = "News entry file name incorrectly formatted"

        status = (description, StatusState.ERROR)

    print(status)


if __name__ == "__main__":
    main()
