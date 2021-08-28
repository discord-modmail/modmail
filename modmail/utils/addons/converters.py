from __future__ import annotations

import re
from typing import TYPE_CHECKING, Type

from discord.ext import commands

from modmail.utils.addons.models import Addon, Plugin

if TYPE_CHECKING:
    from discord.ext.commands import Context

ZIP_REGEX: re.Pattern = re.compile(
    r"^(?:https?:\/\/)?(?P<url>(?P<domain>.*\..+?)\/(?P<path>.*\.zip)) (?P<addon>[^@\s]+)$"
)
REPO_REGEX: re.Pattern = re.compile(
    r"^(?:(?:https?:\/\/)?(?P<githost>github|gitlab)(?:\.com\/| )?)?"
    # github allows usernames from 1 to 39 characters, and projects of 1 to 100 characters
    # gitlab allows 255 characters in the username, and 255 max in a project path
    # see https://gitlab.com/gitlab-org/gitlab/-/issues/197976 for more details
    r"(?P<user>[a-zA-Z0-9][a-zA-Z0-9\-]{0,254})\/(?P<repo>[\w\-\.]{1,100}) "
    r"(?P<addon>[^@\s]+)(?: \@(?P<reflike>[\w\.\s]*))?$"
)


AddonClass = Type[Addon]


class AddonConverter(commands.Converter):
    """A converter that takes an addon source, and gets a Addon object from it."""

    async def convert(self, ctx: Context, argument: str, cls: AddonClass) -> Addon:
        """Convert a string in to an Addon."""
        match = ZIP_REGEX.fullmatch(argument)
        if match is not None:
            # we've matched, so its a zip
            ...

        match = REPO_REGEX.fullmatch(argument)
        if match is None:
            raise commands.BadArgument(f"{argument} is not a valid source.")
        return ...


class PluginWithSourceConverter(AddonConverter):
    """A plugin converter that takes a source, addon name, and returns a Plugin."""

    async def convert(self, ctx: Context, argument: str) -> Plugin:
        """Convert a provided plugin and source to a Plugin."""
        super().convert(ctx, argument, cls=Plugin)
