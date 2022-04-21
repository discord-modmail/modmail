import logging
import re
from typing import TYPE_CHECKING, Tuple

from discord.ext import commands

from modmail.addons.models import AddonSource, Plugin, SourceTypeEnum


if TYPE_CHECKING:
    from modmail.log import ModmailLogger

LOCAL_REGEX = re.compile(r"^\@local (?P<addon>[^@\s]+)$")
ZIP_REGEX = re.compile(
    r"^(?:https?:\/\/)?(?P<url>(?P<domain>.*\..+?)\/(?P<path>.*\.zip)) (?P<addon>[^@\s]+)$"
)
REPO_REGEX = re.compile(
    r"^(?:(?:https?:\/\/)?(?P<githost>github|gitlab)(?:\.com\/| )?)?"
    # github allows usernames from 1 to 39 characters, and projects of 1 to 100 characters
    # gitlab allows 255 characters in the username, and 255 max in a project path
    # see https://gitlab.com/gitlab-org/gitlab/-/issues/197976 for more details
    r"(?P<user>[a-zA-Z0-9][a-zA-Z0-9\-]{0,254})\/(?P<repo>[\w\-\.]{1,100}) "
    r"(?P<addon>[^@]+[^\s@])(?: \@(?P<reflike>[\w\.\-\S]*))?"
)

logger: "ModmailLogger" = logging.getLogger(__name__)


class AddonConverter(commands.Converter):
    """A converter that takes an addon source, and gets a Addon object from it."""

    async def convert(self, ctx: commands.Context, argument: str) -> None:
        """Convert an argument into an Addon."""
        raise NotImplementedError("Inheriting classes must overwrite this method.")


class SourceAndPluginConverter(AddonConverter):
    """A plugin converter that takes a source, addon name, and returns a Plugin."""

    async def convert(self, _: commands.Context, argument: str) -> Tuple[Plugin, AddonSource]:
        """Convert a provided plugin and source to a Plugin."""
        if match := LOCAL_REGEX.match(argument):
            logger.debug("Matched as a local file, creating a Plugin without a source url.")
            addon = match.group("addon")
            source = AddonSource(None, SourceTypeEnum.LOCAL)
        elif match := ZIP_REGEX.fullmatch(argument):
            logger.debug("Matched as a zip, creating a Plugin from zip.")
            addon = match.group("addon")
            source = AddonSource.from_zip(match.group("url"))
        elif match := REPO_REGEX.fullmatch(argument):
            addon = match.group("addon")
            source = AddonSource.from_repo(
                match.group("user"),
                match.group("repo"),
                match.group("reflike"),
                match.group("githost") or "github",
            )
        else:
            raise commands.BadArgument(f"{argument} is not a valid source and plugin.")

        return Plugin(addon), source
