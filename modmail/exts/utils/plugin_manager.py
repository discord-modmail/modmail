# original source:
# https://github.com/python-discord/bot/blob/a8869b4d60512b173871c886321b261cbc4acca9/bot/exts/utils/extensions.py  # noqa: E501
# MIT License 2021 Python Discord
import functools
import logging
import typing as t
from enum import Enum
from pathlib import Path

from discord import Colour, Embed
from discord.ext import commands
from discord.ext.commands import Context, group

from modmail import plugins
from modmail.bot import ModmailBot
from modmail.log import ModmailLogger
from modmail.utils.cogs import ExtMetadata
from modmail.utils.plugin_manager import PLUGINS, unqualify

log: ModmailLogger = logging.getLogger(__name__)

BASE_PATH = Path(plugins.__file__).parent
BASE_PATH_LEN = len(plugins.__name__.split("."))

EXT_METADATA = ExtMetadata(production=True, develop=True, plugin_dev=True)


class Action(Enum):
    """Represents an action to perform on an plugin."""

    # Need to be partial otherwise they are considered to be function definitions.
    LOAD = functools.partial(ModmailBot.load_extension)
    UNLOAD = functools.partial(ModmailBot.unload_extension)
    RELOAD = functools.partial(ModmailBot.reload_extension)


class Plugin(commands.Converter):
    """
    Fully qualify the name of an plugin and ensure it exists.

    The * and ** values bypass this when used with the reload command.
    """

    async def convert(self, ctx: Context, argument: str) -> str:
        """Fully qualify the name of an plugin and ensure it exists."""
        # Special values to reload all plugins
        if argument == "*" or argument == "**":
            return argument

        argument = argument.lower()
        plugs = []
        for ext, _nul in PLUGINS:
            plugs.append(ext)

        if argument in plugs:
            return argument
        elif (qualified_arg := f"{plugins.__name__}.{argument}") in PLUGINS:
            return qualified_arg

        matches = []
        for ext in plugs:
            if argument == unqualify(ext):
                matches.append(ext)

        if len(matches) > 1:
            matches.sort()
            names = "\n".join(matches)
            raise commands.BadArgument(
                f":x: `{argument}` is an ambiguous plugin name. "
                f"Please use one of the following fully-qualified names.```\n{names}```"
            )
        elif matches:
            return matches[0]
        else:
            raise commands.BadArgument(f":x: Could not find the plugin `{argument}`.")


class PluginManager(commands.Cog, name="Plugin Manager"):
    """Plugin management commands."""

    def __init__(self, bot: ModmailBot):
        self.bot = bot

    @group(name="plugins", aliases=("plug", "plugs", "plugin"), invoke_without_command=True)
    async def plugins_group(self, ctx: Context) -> None:
        """Load, unload, reload, and list loaded plugins."""
        await ctx.send_help(ctx.command)

    @plugins_group.command(name="load", aliases=("l",))
    async def load_command(self, ctx: Context, *plugs: Plugin) -> None:
        r"""
        Load plugins given their fully qualified or unqualified names.

        If '\*' or '\*\*' is given as the name, all unloaded plugins will be loaded.
        """  # noqa: W605
        if not plugs:
            await ctx.send_help(ctx.command)
            return

        if "*" in plugs or "**" in plugs:
            plugs = set(PLUGINS) - set(self.bot.extensions.keys())

        msg = self.batch_manage(Action.LOAD, *plugs)
        await ctx.send(msg)

    @plugins_group.command(name="unload", aliases=("ul",))
    async def unload_command(self, ctx: Context, *plugs: Plugin) -> None:
        r"""
        Unload currently loaded plugins given their fully qualified or unqualified names.

        If '\*' or '\*\*' is given as the name, all loaded plugins will be unloaded.
        """  # noqa: W605
        if not plugs:
            await ctx.send_help(ctx.command)
            return

        if "*" in plugs or "**" in plugs:
            plugs = set(self.bot.extensions.keys())

        msg = self.batch_manage(Action.UNLOAD, *plugs)

        await ctx.send(msg)

    @plugins_group.command(name="reload", aliases=("r",))
    async def reload_command(self, ctx: Context, *plugs: Plugin) -> None:
        r"""
        Reload plugins given their fully qualified or unqualified names.

        If an plugin fails to be reloaded, it will be rolled-back to the prior working state.

        If '\*' is given as the name, all currently loaded plugins will be reloaded.
        If '\*\*' is given as the name, all plugins, including unloaded ones, will be reloaded.
        """  # noqa: W605
        if not plugs:
            await ctx.send_help(ctx.command)
            return

        if "**" in plugs:
            plugs = []
            for plug, _nul in PLUGINS:
                plugs.append(plug)
        elif "*" in plugs:
            plugs = set(self.bot.extensions.keys()) | set(plugs)
            plugs.remove("*")

        msg = self.batch_manage(Action.RELOAD, *plugs)

        await ctx.send(msg)

    @plugins_group.command(name="list", aliases=("all",))
    async def list_command(self, ctx: Context) -> None:
        """
        Get a list of all plugins, including their loaded status.

        Grey indicates that the plugins is unloaded.
        Green indicates that the plugins is currently loaded.
        """
        embed = Embed(colour=Colour.blurple())
        embed.set_author(
            name="Plugins List",
        )

        lines = []
        categories = self.group_plugin_statuses()
        for category, plugs in sorted(categories.items()):
            # Treat each category as a single line by concatenating everything.
            # This ensures the paginator will not cut off a page in the middle of a category.
            category = category.replace("_", " ").title()
            plugs = "\n".join(sorted(plugs))
            lines.append(f"**{category}**\n{plugs}\n")

        log.debug(f"{ctx.author} requested a list of all cogs. Returning a list.")
        # await Paginator.paginate(lines, ctx, embed, scale_to_size=700, empty=False)

        # since we currently don't have a paginator.
        output = ""
        for line in lines:
            output += line
        await ctx.send(output)

    def group_plugin_statuses(self) -> t.Mapping[str, str]:
        """Return a mapping of plugin names and statuses to their categories."""
        categories = {}
        plugs = []
        for ext, _nul in PLUGINS:
            plugs.append(ext)
        for plug in plugs:
            if plug in self.bot.extensions:
                status = ":green_circle:"
            else:
                status = ":red_circle:"

            path = ext.split(".")
            if len(path) > BASE_PATH_LEN + 1:
                category = " - ".join(path[BASE_PATH_LEN:-1])
            else:
                category = "uncategorised"

            categories.setdefault(category, []).append(f"{status}  {path[-1]}")

        return categories

    def batch_manage(self, action: Action, *plugs: str) -> str:
        """
        Apply an action to multiple plugins and return a message with the results.

        If only one plugin is given, it is deferred to `manage()`.
        """
        if len(plugs) == 1:
            msg, _ = self.manage(action, plugs[0])
            return msg

        verb = action.name.lower()
        failures = {}

        for plug in plugs:
            _, error = self.manage(action, plug)
            if error:
                failures[plug] = error

        emoji = ":x:" if failures else ":ok_hand:"
        msg = f"{emoji} {len(plugs) - len(failures)} / {len(plugs)} plugins {verb}ed."

        if failures:
            failures = "\n".join(f"{ext}\n    {err}" for ext, err in failures.items())
            msg += f"\nFailures:```\n{failures}```"

        log.debug(f"Batch {verb}ed plugins.")

        return msg

    def manage(self, action: Action, plug: str) -> t.Tuple[str, t.Optional[str]]:
        """Apply an action to an plugin and return the status message and any error message."""
        verb = action.name.lower()
        error_msg = None

        try:
            action.value(self.bot, plug)
        except (commands.ExtensionAlreadyLoaded, commands.ExtensionNotLoaded):
            if action is Action.RELOAD:
                # When reloading, just load the plugin if it was not loaded.
                log.debug("Treating {plug!r} as if it was not loaded.")
                return self.manage(Action.LOAD, plug)

            msg = f":x: Plugin `{plug}` is already {verb}ed."
            log.debug(msg[4:])
        except Exception as e:
            if hasattr(e, "original"):
                e = e.original

            log.exception(f"Plugin '{plug}' failed to {verb}.")

            error_msg = f"{e.__class__.__name__}: {e}"
            msg = f":x: Failed to {verb} plugin `{plug}`:\n```\n{error_msg}```"
        else:
            msg = f":ok_hand: Plugin successfully {verb}ed: `{plug}`."
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


def setup(bot: ModmailBot) -> None:
    """Load the Plugins manager cog."""
    bot.add_cog(PluginManager(bot))
