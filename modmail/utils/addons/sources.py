from __future__ import annotations

import re
from enum import Enum
from re import Pattern
from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from discord.ext.commands import Context

ZIP_REGEX: Pattern = re.compile(r"^(?P<url>^(?:https?:\/\/)?.*\..+\/.*\.zip) ?(?P<plugin>[^@\s]+)?$")
REPO_REGEX: Pattern = re.compile(
    r"^(?:(?:https?:\/\/)?(?P<githost>github|gitlab)(?:\.com\/| )?)?"
    # github allows usernames from 1 to 39 characters, and projects of 1 to 100 characters
    # gitlab allows 255 characters in the username, and 255 max in a project path
    # see https://gitlab.com/gitlab-org/gitlab/-/issues/197976 for more details
    r"(?P<user>[a-zA-Z0-9][a-zA-Z0-9\-]{0,254})\/(?P<repo>[\w\-\.]{1,100}) "
    r"(?P<plugin>[^@\s]+) ?(?P<reflike>\@[\w\.\s]*)?$"
)


class AddonSourceEnum(Enum):
    """Source Types."""

    GITHUB = "github"
    GITLAB = "gitlab"
    LOCAL = ".local"
    ZIP = ".zip"


class AddonSource:
    """
    Represents an AddonSource.

    These could be from github, gitlab, a hosted zip file, or local.
    """

    def __init__(self, type: AddonSourceEnum, match: re.Match = None, url: str = None) -> AddonSource:
        """Initialize the AddonSource."""
        self.type = type
        self.url = url
        if match is not None and (type == AddonSourceEnum.GITHUB or type == AddonSourceEnum.GITLAB):
            # this is a repository, so we have extra metadata
            self.user = match.group("user")
            self.repo = match.group("repo")
            self.githost = match.group("githost") or "github"
            self.ref = match.group("reflike")
            self.base_link = f"https://{self.githost}.com/{self.user}/{self.repo}"
            if url is None:
                self.url = ...


class AddonSourceConverter(commands.Converter):
    """A converter that takes an addon source, and gets a Source object from it."""

    async def convert(self, ctx: Context, argument: str) -> AddonSource:
        """Convert a string in to an AddonSource."""
        match = ZIP_REGEX.fullmatch(argument)
        if match is not None:
            # we've matched, so its a zip
            ...
        match = REPO_REGEX.fullmatch(argument)
        if match is None:
            raise commands.BadArgument(f"{argument} is not a valid source.")
