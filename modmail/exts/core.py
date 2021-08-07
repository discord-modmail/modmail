# original source:
# https://github.com/python-discord/bot/blob/a8869b4d60512b173871c886321b261cbc4acca9/bot/exts/utils/extensions.py  # noqa: E501
# MIT License 2021 Python Discord
import functools
import logging
import typing as t
from enum import Enum

from discord import Colour, Embed
from discord.ext import commands
from discord.ext.commands import Context

from modmail import exts
from modmail.bot import ModmailBot
from modmail.log import ModmailLogger
from modmail.utils.cogs import ExtMetadata
from modmail.utils.extensions import EXTENSIONS, unqualify
from modmail.utils.plugin_manager import PLUGINS

log: ModmailLogger = logging.getLogger(__name__)

BASE_PATH = exts.__name__.count(".") + 1

EXT_METADATA = ExtMetadata(production=True, develop=True, plugin_dev=True)


class Action(Enum):
    """Represents an action to perform on an extension."""

    # Need to be partial otherwise they are considered to be function definitions.
    LOAD = functools.partial(ModmailBot.load_extension)
    UNLOAD = functools.partial(ModmailBot.unload_extension)
    RELOAD = functools.partial(ModmailBot.reload_extension)


class ExtensionConverter(commands.Converter):
    """
    Fully qualify the name of an extension and ensure it exists.

    The * and ** values bypass this when used with the reload command.
    """

    source_list = EXTENSIONS
    type = "extension"

    async def convert(self, ctx: Context, argument: str) -> str:
        """Fully qualify the name of an extension and ensure it exists."""
        # Special values to reload all extensions
        if argument == "*" or argument == "**":
            return argument

        argument = argument.lower()

        if argument in self.source_list:
            return argument

        qualified_arg = f"{exts.__name__}.{argument}"
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


class PluginConverter(ExtensionConverter):
    """
    Fully qualify the name of a plugin and ensure it exists.

    The * and ** values bypass this when used with the reload command.
    """

    source_list = PLUGINS
    type = "plugin"


class ExtensionManager(commands.Cog):
    """Extension management base class."""

    def __init__(self, bot: ModmailBot):
        self.bot = bot
        self.all_extensions = EXTENSIONS

    async def get_black_listed_extensions() -> list:
        """Returns a list of all blacklisted extensions."""
        raise NotImplementedError()

    @commands.group("ext", aliases=("extensions",))
    async def extensions_group(self, ctx: Context) -> None:
        """Load, unload, reload, and list loaded extensions."""
        await ctx.send_help(ctx.command)

    @extensions_group.command(name="load", aliases=("l",))
    async def load_command(self, ctx: Context, *extensions: ExtensionConverter) -> None:
        """
        Load extensions given their fully qualified or unqualified names.

        If '\*' or '\*\*' is given as the name, all unloaded extensions will be loaded.
        """  # noqa: W605
        if not extensions:
            await ctx.send_help(ctx.command)
            return

        if "*" in extensions or "**" in extensions:
            extensions = sorted(ext for ext in self.all_extensions if ext not in self.bot.extensions.keys())

        msg = self.batch_manage(Action.LOAD, *extensions)
        await ctx.send(msg)

    @extensions_group.command(name="unload", aliases=("ul",))
    async def unload_command(self, ctx: Context, *extensions: ExtensionConverter) -> None:
        """
        Unload currently loaded extensions given their fully qualified or unqualified names.

        If '\*' or '\*\*' is given as the name, all loaded extensions will be unloaded.
        """  # noqa: W605
        if not extensions:
            await ctx.send_help(ctx.command)
            return

        blacklisted = [ext for ext in await self.get_black_listed_extensions() if ext in extensions]

        if blacklisted:
            bl_msg = "\n".join(blacklisted)
            await ctx.send(f":x: The following extension(s) may not be unloaded:```\n{bl_msg}```")
            return

        if "*" in extensions or "**" in extensions:
            extensions = sorted(ext for ext in self.bot.extensions.keys() if ext not in blacklisted)

        await ctx.send(self.batch_manage(Action.UNLOAD, *extensions))

    @extensions_group.command(name="reload", aliases=("r",))
    async def reload_command(self, ctx: Context, *extensions: ExtensionConverter) -> None:
        """
        Reload extensions given their fully qualified or unqualified names.

        If an extension fails to be reloaded, it will be rolled-back to the prior working state.

        If '*' is given as the name, all currently loaded extensions will be reloaded.
        If '**' is given as the name, all extensions, including unloaded ones, will be reloaded.
        """
        if not extensions:
            await ctx.send_help(ctx.command)
            return

        if "**" in extensions:
            extensions = self.all_extensions.keys()
        elif "*" in extensions:
            extensions = [*extensions, *sorted(self.bot.extensions.keys())]
            extensions.remove("*")

        await ctx.send(self.batch_manage(Action.RELOAD, *extensions))

    @extensions_group.command(name="list", aliases=("all",))
    async def list_command(self, ctx: Context) -> None:
        """
        Get a list of all extensions, including their loaded status.

        Grey indicates that the extension is unloaded.
        Green indicates that the extension is currently loaded.
        """
        embed = Embed(colour=Colour.blurple())
        embed.set_author(
            name="Extensions List",
        )

        lines = []
        categories = self.group_extension_statuses()
        for category, extensions in sorted(categories.items()):
            # Treat each category as a single line by concatenating everything.
            # This ensures the paginator will not cut off a page in the middle of a category.
            category = category.replace("_", " ").title()
            extensions = "\n".join(sorted(extensions))
            lines.append(f"**{category}**\n{extensions}\n")

        log.debug(f"{ctx.author} requested a list of all extensions. " "Returning a paginated list.")

        # since we currently don't have a paginator.
        await ctx.send("".join(lines))

    def group_extension_statuses(self) -> t.Mapping[str, str]:
        """Return a mapping of extension names and statuses to their categories."""
        categories = {}

        for ext in self.all_extensions.keys():
            if ext in self.bot.extensions:
                status = ":green_circle:"
            else:
                status = ":red_circle:"

            root, name = ext.rsplit(".", 1)
            if len(root) > len(BASE_PATH):
                category = " - ".join(root[len(BASE_PATH) + 1 :].split("."))
            else:
                category = "uncategorized"

            categories.setdefault(category, []).append(f"{status}  {name}")

        return categories

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

        emoji = ":x:" if failures else ":ok_hand:"
        msg = f"{emoji} {len(extensions) - len(failures)} / {len(extensions)} extensions {verb}ed."

        if failures:
            failures = "\n".join(f"{ext}\n    {err}" for ext, err in failures.items())
            msg += f"\nFailures:```\n{failures}```"

        log.debug(f"Batch {verb}ed extensions.")

        return msg

    def manage(self, action: Action, ext: str) -> t.Tuple[str, t.Optional[str]]:
        """Apply an action to an extension and return the status message and any error message."""
        verb = action.name.lower()
        error_msg = None

        try:
            action.value(self.bot, ext)
        except (commands.ExtensionAlreadyLoaded, commands.ExtensionNotLoaded):
            if action is Action.RELOAD:
                # When reloading, just load the extension if it was not loaded.
                log.debug("Treating {ext!r} as if it was not loaded.")
                return self.manage(Action.LOAD, ext)

            msg = f":x: Extension `{ext}` is already {verb}ed."
            log.debug(msg[4:])
        except Exception as e:
            if hasattr(e, "original"):
                e = e.original

            log.exception(f"Extension '{ext}' failed to {verb}.")

            error_msg = f"{e.__class__.__name__}: {e}"
            msg = f":x: Failed to {verb} extension `{ext}`:\n```\n{error_msg}```"
        else:
            msg = f":ok_hand: Extension successfully {verb}ed: `{ext}`."
            log.debug(msg[10:])

        return msg, error_msg

    # This cannot be static (must have a __func__ attribute).
    async def cog_check(self, ctx: Context) -> bool:
        """Only allow bot owners to invoke the commands in this cog."""
        return await self.bot.is_owner(ctx.author)

    # This cannot be static (must have a __func__ attribute).
    async def cog_command_error(self, ctx: Context, error: Exception) -> None:
        """Handle BadArgument errors locally to prevent the help command from showing."""
        if isinstance(error, commands.BadArgument):
            await ctx.send(str(error))
            error.handled = True


class PluginsManager(ExtensionManager):
    """Plugin management commands."""

    def __init__(self, bot: ModmailBot) -> None:
        super().__init__(bot)

    @commands.group("plugins", aliases=("plug", "plugs", "plugins"))
    async def plugins_group(self, ctx: Context) -> None:
        """Install, uninstall, disable, update, and enable installed plugins."""
        await ctx.send_help(ctx.command)

    # Not implemented


def setup(bot: ModmailBot) -> None:
    """Load the Plugins manager cog."""
    bot.add_cog(ExtensionManager(bot))
    bot.add_cog(PluginsManager(bot))
