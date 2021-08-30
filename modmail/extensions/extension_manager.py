# original source:
# https://github.com/python-discord/bot/blob/a8869b4d60512b173871c886321b261cbc4acca9/bot/exts/utils/extensions.py  # noqa: E501
# MIT License 2021 Python Discord
import functools
import logging
import typing as t
from collections import defaultdict
from enum import Enum

from discord import AllowedMentions, Colour, Embed
from discord.ext import commands
from discord.ext.commands import Context

from modmail.bot import ModmailBot
from modmail.log import ModmailLogger
from modmail.utils.cogs import BotModes, ExtMetadata, ModmailCog
from modmail.utils.extensions import EXTENSIONS, NO_UNLOAD, unqualify, walk_extensions

log: ModmailLogger = logging.getLogger(__name__)


BASE_PATH_LEN = __name__.count(".")

EXT_METADATA = ExtMetadata(load_if_mode=BotModes.DEVELOP, no_unload=True)


class Action(Enum):
    """Represents an action to perform on an extension."""

    # Need to be partial otherwise they are considered to be function definitions.
    LOAD = functools.partial(ModmailBot.load_extension)
    UNLOAD = functools.partial(ModmailBot.unload_extension)
    RELOAD = functools.partial(ModmailBot.reload_extension)


class ExtensionConverter(commands.Converter):
    """
    Fully qualify the name of an extension and ensure it exists.

    The * value bypasses this when used with an extension manger command.
    """

    source_list = EXTENSIONS
    type = "extension"

    async def convert(self, _: Context, argument: str) -> str:
        """Fully qualify the name of an extension and ensure it exists."""
        # Special values to reload all extensions
        if argument == "*":
            return argument

        argument = argument.lower()

        if argument in self.source_list:
            return argument

        qualified_arg = f"modmail.{self.type}s.{argument}"
        if qualified_arg in self.source_list:
            return qualified_arg

        matches = []
        for ext in self.source_list:
            if argument == unqualify(ext):
                matches.append(ext)

        if not matches:
            raise commands.BadArgument(f":x: Could not find the {self.type} `{argument}`.")

        if len(matches) > 1:
            names = "\n".join(sorted(matches))
            raise commands.BadArgument(
                f":x: `{argument}` is an ambiguous {self.type} name. "
                f"Please use one of the following fully-qualified names.```\n{names}```"
            )

        return matches[0]


class ExtensionManager(ModmailCog, name="Extension Manager"):
    """
    Extension management.

    Commands to load, reload, unload, and list extensions.
    """

    type = "extension"

    def __init__(self, bot: ModmailBot):
        self.bot = bot
        self.all_extensions = EXTENSIONS
        self.refresh_method = walk_extensions

    def get_black_listed_extensions(self) -> list:
        """Returns a list of all unload blacklisted extensions."""
        return NO_UNLOAD

    @commands.group("ext", aliases=("extensions", "exts"), invoke_without_command=True)
    async def extensions_group(self, ctx: Context) -> None:
        """Load, unload, reload, and list loaded extensions."""
        await ctx.send_help(ctx.command)

    @extensions_group.command(name="load", aliases=("l",))
    async def load_extensions(self, ctx: Context, *extensions: ExtensionConverter) -> None:
        r"""
        Load extensions given their fully qualified or unqualified names.

        If '\*' is given as the name, all unloaded extensions will be loaded.
        """
        if not extensions:
            await ctx.send_help(ctx.command)
            return

        if "*" in extensions:
            extensions = sorted(ext for ext in self.all_extensions if ext not in self.bot.extensions.keys())

        msg = self.batch_manage(Action.LOAD, *extensions)
        await ctx.send(msg)

    @extensions_group.command(name="unload", aliases=("ul",))
    async def unload_extensions(self, ctx: Context, *extensions: ExtensionConverter) -> None:
        r"""
        Unload currently loaded extensions given their fully qualified or unqualified names.

        If '\*' is given as the name, all loaded extensions will be unloaded.
        """
        if not extensions:
            await ctx.send_help(ctx.command)
            return

        blacklisted = [ext for ext in self.get_black_listed_extensions() if ext in extensions]

        if blacklisted:
            bl_msg = "\n".join(blacklisted)
            await ctx.send(f":x: The following {self.type}(s) may not be unloaded:```\n{bl_msg}```")
            return

        if "*" in extensions:
            extensions = sorted(
                ext
                for ext in self.bot.extensions.keys() & self.all_extensions
                if ext not in (self.get_black_listed_extensions())
            )

        await ctx.send(self.batch_manage(Action.UNLOAD, *extensions))

    @extensions_group.command(name="reload", aliases=("r", "rl"))
    async def reload_extensions(self, ctx: Context, *extensions: ExtensionConverter) -> None:
        r"""
        Reload extensions given their fully qualified or unqualified names.

        If an extension fails to be reloaded, it will be rolled-back to the prior working state.

        If '\*' is given as the name, all currently loaded extensions will be reloaded.
        """
        if not extensions:
            await ctx.send_help(ctx.command)
            return

        if "*" in extensions:
            extensions = self.bot.extensions.keys() & self.all_extensions.keys()

        await ctx.send(self.batch_manage(Action.RELOAD, *extensions))

    @extensions_group.command(name="list", aliases=("all", "ls"))
    async def list_extensions(self, ctx: Context) -> None:
        """
        Get a list of all extensions, including their loaded status.

        Red indicates that the extension is unloaded.
        Green indicates that the extension is currently loaded.
        """
        embed = Embed(colour=Colour.blurple())
        embed.set_author(
            name=f"{self.type.capitalize()} List",
        )

        lines = []
        categories = self.group_extension_statuses()
        for category, extensions in sorted(categories.items()):
            # Treat each category as a single line by concatenating everything.
            # This ensures the paginator will not cut off a page in the middle of a category.
            category = category.replace("_", " ").title()
            extensions = "\n".join(sorted(extensions))
            lines.append(f"**{category}**\n{extensions}\n")

        log.debug(f"{ctx.author} requested a list of all {self.type}s. " "Returning a paginated list.")

        # TODO: since we currently don't have a paginator.
        await ctx.send("".join(lines) or f"There are no {self.type}s installed.")

    @extensions_group.command(name="refresh", aliases=("rewalk", "rescan"))
    async def resync_extensions(self, ctx: Context) -> None:
        """
        Refreshes the list of extensions from disk, but do not unload any currently active.

        Typical use case is in the event that the existing extensions have changed while the bot is running.
        """
        log.debug(f"Refreshing list of {self.type}s.")

        # make sure the new walk contains all currently loaded extensions, so they can be unloaded
        loaded_extensions = {}
        for name, should_load in self.all_extensions.items():
            if name in self.bot.extensions:
                loaded_extensions[name] = should_load

        # now that we know what the list was, we can clear it
        self.all_extensions.clear()
        # put the loaded extensions back in
        self.all_extensions.update(loaded_extensions)
        # now we can re-walk the extensions
        self.all_extensions.update(self.refresh_method())
        await ctx.send(f":ok_hand: Refreshed list of {self.type}s.")

    def group_extension_statuses(self) -> t.Mapping[str, str]:
        """Return a mapping of extension names and statuses to their categories."""
        categories = defaultdict(list)

        for ext in self.all_extensions:
            if ext in self.bot.extensions:
                status = ":green_circle:"
            else:
                status = ":red_circle:"

            root, name = ext.rsplit(".", 1)
            category = " - ".join(root.split("."))
            categories[category].append(f"{status}  {name}")

        return dict(categories)

    def batch_manage(self, action: Action, *extensions: str) -> str:
        """
        Apply an action to multiple extensions and return a message with the results.

        If only one extension is given, it is deferred to `manage()`.
        """
        if len(extensions) == 1:
            msg, _ = self.manage(action, extensions[0])
            return msg

        verb = action.name.lower()
        failures = {}

        for extension in sorted(extensions):
            _, error = self.manage(action, extension)
            if error:
                failures[extension] = error

        emoji = ":x:" if failures else ":thumbsup:"
        msg = f"{emoji} {len(extensions) - len(failures)} / {len(extensions)} {self.type}s {verb}ed."

        if failures:
            failures = "\n".join(f"{ext}\n    {err}" for ext, err in failures.items())
            msg += f"\nFailures:```\n{failures}```"

        log.debug(f"Batch {verb}ed {self.type}s.")

        return msg

    def manage(self, action: Action, ext: str) -> t.Tuple[str, t.Optional[str]]:
        """Apply an action to an extension and return the status message and any error message."""
        verb = action.name.lower()
        error_msg = None

        try:
            action.value(self.bot, ext)
        except (commands.ExtensionAlreadyLoaded, commands.ExtensionNotLoaded):
            if action is Action.RELOAD:
                # When reloading, have a special error.
                msg = f":x: {self.type.capitalize()} `{ext}` is not loaded, so it was not {verb}ed."
            else:
                msg = f":x: {self.type.capitalize()} `{ext}` is already {verb}ed."
        except Exception as e:
            if hasattr(e, "original"):
                # If original exception is present, then utilize it
                e = e.original

            log.exception(f"{self.type.capitalize()} '{ext}' failed to {verb}.")

            error_msg = f"{e.__class__.__name__}: {e}"
            msg = f":x: Failed to {verb} {self.type} `{ext}`:\n```\n{error_msg}```"
        else:
            msg = f":thumbsup: {self.type.capitalize()} successfully {verb}ed: `{ext}`."

        log.debug(error_msg or msg)
        return msg, error_msg

    # This cannot be static (must have a __func__ attribute).
    async def cog_check(self, ctx: Context) -> bool:
        """Only allow bot owners to invoke the commands in this cog."""
        # TODO: Change to allow other users to invoke this too.
        return await self.bot.is_owner(ctx.author)

    # This cannot be static (must have a __func__ attribute).
    async def cog_command_error(self, ctx: Context, error: Exception) -> None:
        """Handle BadArgument errors locally to prevent the help command from showing."""
        if isinstance(error, commands.BadArgument):
            await ctx.send(str(error), allowed_mentions=AllowedMentions.none())
            error.handled = True


def setup(bot: ModmailBot) -> None:
    """Load the Extension Manager cog."""
    bot.add_cog(ExtensionManager(bot))
