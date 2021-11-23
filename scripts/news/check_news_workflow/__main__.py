import pathlib
import re
import sys
from typing import Tuple

import requests


NEWS_NEXT_DIR = "news/next/"
SKIP_NEWS_LABEL = "skip changelog"
GH_API_URL = "https://api.github.com/"
HEADERS = {"accept": "application/vnd.github.v3+json"}
REPO_ORG_NAME = "discord-modmail/modmail"


FILENAME_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}(?:-\d{2}-\d{2}-\d{2})?\."  # match `yyyy-mm-dd` or `yyyy-m-d`
    r"pr-\d+(?:,\d+)*\."  # Issue number(s)
    r"[A-Za-z0-9_=-]+\."  # Nonce (URL-safe base64)
    r"md",  # File extension
    re.VERBOSE,
)


def is_news_dir(filename: str) -> bool:
    """Return True if file is in the News directory."""
    return filename.startswith(NEWS_NEXT_DIR)


def main(pr: int) -> Tuple[str, bool]:
    """Main function to check for a changelog entry."""
    r = requests.get(f"{GH_API_URL}repos/{REPO_ORG_NAME}/pulls/{pr}/files", headers=HEADERS)
    files_changed = r.json()
    in_next_dir = file_found = False

    for file in files_changed:
        if not is_news_dir(file["filename"]):
            continue
        in_next_dir = True
        file_path = pathlib.PurePath(file["filename"])
        if len(file_path.parts) != 4:  # news, next, <type>, <entry>
            continue
        file_found = True
        if FILENAME_RE.match(file_path.name) and len(file["patch"]) >= 1:
            status = (f"News entry found in {NEWS_NEXT_DIR}", True)
            break
    else:
        _r = requests.get(f"{GH_API_URL}repos/{REPO_ORG_NAME}/pulls/{pr}", headers=HEADERS)
        pr_data = _r.json()
        labels = [label["name"] for label in pr_data["labels"]]
        if SKIP_NEWS_LABEL in labels:
            status = (f"'{SKIP_NEWS_LABEL}' label found", True)
        else:
            if not in_next_dir:
                status = (f'No news entry in {NEWS_NEXT_DIR} or "{SKIP_NEWS_LABEL}" label found', False)
            elif not file_found:
                status = ("News entry not in an appropriate directory", False)
            else:
                status = ("News entry file name incorrectly formatted", False)

    return status


if __name__ == "__main__":
    message, status = main(int(sys.argv[1]))
    print(message)
    sys.exit(0 if status else 1)
