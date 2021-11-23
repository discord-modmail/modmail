import os
from pathlib import Path

import modmail


PR_ENDPOINT = "https://api.github.com/repos/discord-modmail/modmail/pulls/{number}"
BAD_RESPONSE = {
    404: "Pull request not located! Please enter a valid number!",
    403: "Rate limit has been hit! Please try again later!",
}

TEMPLATE_FILE_PATH = Path(Path(__file__).parent, "template.md.jinja")
REPO_ROOT = Path(modmail.__file__).parent.parent
NEWS_NEXT = Path(REPO_ROOT, "news/next")

ERROR_MSG_PREFIX = "Oh no! 💥 💔 💥"
TEMPLATE = """
# Please write your news content. When finished, save the file.
# In order to abort, exit without saving.
# Lines starting with "#" are ignored.

""".lstrip()
NO_NEWS_PATH_ERROR = (
    f"{ERROR_MSG_PREFIX} {Path(os.path.relpath(NEWS_NEXT, start=Path.cwd()))} doesn't exist, please create it"
    f" and run this command again :) Happy change-logging!"
)

SECTIONS = {
    "feature": "Features",
    "trivial": "Trivial/Internal Changes",
    "improvement": "Improvements",
    "bugfix": "Bug Fixes",
    "doc": "Improved Documentation",
    "deprecation": "Deprecations",
    "breaking": "Breaking Changes",
    "internal": "Internal",
}
