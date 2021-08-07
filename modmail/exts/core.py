# original source:
# https://github.com/python-discord/bot/blob/a8869b4d60512b173871c886321b261cbc4acca9/bot/exts/utils/extensions.py  # noqa: E501
# MIT License 2021 Python Discord
import functools
import logging
import typing as t
from enum import Enum

from discord import Colour, Embed
from discord.ext import commands
from discord.ext.commands import Context, Group, command

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


class Extension(commands.Converter):
    """
    Fully qualify the name of an extension and ensure it exists.

    The * and ** values bypass this when used with the reload command.
    """

    async def convert(self, ctx: Context, argument: str) -> str:
        """Fully qualify the name of an extension and ensure it exists."""
        if (ctx.command.name).lower() == "cog":
            extensions_all = EXTENSIONS
        elif (ctx.command.name).lower() == "plugin":
            extensions_all = PLUGINS

        # Special values to reload all extensions
        if argument == "*" or argument == "**":
            return argument

        argument = argument.lower()

        if argument in extensions_all.keys():
            return argument

        if (qualified_arg := f"{exts.__name__}.{argument}") in extensions_all.keys():
            return qualified_arg

        matches = []
        for ext in extensions_all:
            if argument == unqualify(ext):
                matches.append(ext)

        if not matches:
            raise commands.BadArgument(f":x: Could not find the extension `{argument}`.")
        elif len(matches) > 1:
            names = "\n".join(sorted(matches))
            raise commands.BadArgument(
                f":x: `{argument}` is an ambiguous extension name. "
                f"Please use one of the following fully-qualified names.```\n{names}```"
            )
        else:
            return matches[0]


def custom_group() -> t.Callable:
    """
    Custom command `group` decorator.

    Reads the `name` and `alias` attributes from the decorator and passes it on to the group.
    """

    def decorator(function: t.Callable) -> t.Callable:
        @functools.wraps(function)
        def wrapper(self: t.Any, *args) -> commands.Command:
            args.setdefault("cls", Group)
            return command(
                name=self.extension_type,
                aliases=self.aliases,
                help=f"Load, unload, reload, and list loaded {self.extension_type}.",
                **args,
            )

        return wrapper

    return decorator


class ExtensionManager(commands.Cog):
    """Extension management base class."""

    def __init__(self, bot: ModmailBot, extension_type: str, aliases: t.Optional[t.Tuple[str]] = None):
        self.bot = bot
        self.extension_type = extension_type.lower()
        self.aliases = aliases or ()

        _all_mapping = {"cog": EXTENSIONS.copy(), "plugin": PLUGINS.copy()}
        self.all_extensions = _all_mapping.get(extension_type)

        if not self.all_extensions:
            raise ValueError(
                f"Looks like you have given an incorrect {extension_type}, "
                "valid options are: {', '.join(_all_mapping.keys())}"
            )

    async def get_black_listed_extensions() -> list:
        """Returns a list of all blacklisted extensions."""
        raise NotImplementedError()

    @custom_group(invoke_without_command=True)
    async def extensions_group(self, ctx: Context) -> None:
        """Load, unload, reload, and list loaded extensions."""
        await ctx.send_help(ctx.command)

    @extensions_group.command(name="load", aliases=("l",))
    async def load_command(self, ctx: Context, *extensions: Extension) -> None:
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
    async def unload_command(self, ctx: Context, *extensions: Extension) -> None:
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
    async def reload_command(self, ctx: Context, *extensions: Extension) -> None:
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
            extensions = (self.bot.extensions.keys()).extend(extensions)
            extensions.remove("*")

        msg = self.batch_manage(Action.RELOAD, *extensions)

        await ctx.send(msg)

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

        log.debug(
            f"{ctx.author} requested a list of all {self.extension_type.lower()}s. "
            "Returning a paginated list."
        )

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
        self.bot = bot

        _extension_type = "plugin"
        _aliases = ("plug", "plugs", "plugins")
        ExtensionManager.__init__(self, bot, _extension_type, _aliases)


def setup(bot: ModmailBot) -> None:
    """Load the Plugins manager cog."""
    bot.add_cog(PluginsManager(bot))
