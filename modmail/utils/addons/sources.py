from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from discord.ext import commands

if TYPE_CHECKING:
    from discord.ext.commands import Context

ZIP_REGEX: re.Pattern = re.compile(r"^(?P<url>^(?:https?:\/\/)?.*\..+\/.*\.zip) ?(?P<plugin>[^@\s]+)?$")
REPO_REGEX: re.Pattern = re.compile(
    r"^(?:(?:https?:\/\/)?(?P<githost>github|gitlab)(?:\.com\/| )?)?"
    # github allows usernames from 1 to 39 characters, and projects of 1 to 100 characters
    # gitlab allows 255 characters in the username, and 255 max in a project path
    # see https://gitlab.com/gitlab-org/gitlab/-/issues/197976 for more details
    r"(?P<user>[a-zA-Z0-9][a-zA-Z0-9\-]{0,254})\/(?P<repo>[\w\-\.]{1,100}) "
    r"(?P<plugin>[^@\s]+) ?(?P<reflike>\@[\w\.\s]*)?$"
)


class GitHost:
    """Base class for git hosts."""

    pass


class Github(GitHost):
    """Github's api."""

    headers = {"Accept": "application/vnd.github.v3+json"}
    base_api_url = "https://api.github.com"
    repo_api_url = f"{base_api_url}/repos/{{user}}/{{repo}}"
    zip_archive_api_url = f"{repo_api_url}/zipball"


class Gitlab(GitHost):
    """Gitlab's api."""

    headers = {}
    base_api_url = "https://gitlab.com/api/v4"
    repo_api_url = f"{base_api_url}/projects/{{user}}%2F{{repo}}"
    zip_archive_api_url = f"{repo_api_url}/repository/archive.zip"


class AddonSource:
    """
    Represents an AddonSource.

    These could be from github, gitlab, or hosted zip file.
    """

    def __init__(self, type: Any, url: str) -> AddonSource:
        """Initialize the AddonSource."""
        self.type = type
        self.url = url
        if self.type == "github":
            ...


class AddonConverter(commands.Converter):
    """A converter that takes an addon source, and gets a AddonWithSource object from it."""

    async def convert(self, ctx: Context, argument: str) -> AddonSource:
        """Convert a string in to an AddonSource."""
        match = ZIP_REGEX.fullmatch(argument)
        if match is not None:
            # we've matched, so its a zip
            ...

        match = REPO_REGEX.fullmatch(argument)
        if match is None:
            raise commands.BadArgument(f"{argument} is not a valid source.")
