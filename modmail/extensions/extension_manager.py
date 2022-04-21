# original source:
# https://github.com/python-discord/bot/blob/a8869b4d60512b173871c886321b261cbc4acca9/bot/exts/utils/extensions.py  # noqa: E501
# MIT License 2021 Python Discord
import functools
import logging
from collections import defaultdict
from enum import Enum
from typing import Mapping, Tuple, Union

from discord import Colour, Embed
from discord.ext import commands
from discord.ext.commands import Context

import modmail.config
from modmail.bot import ModmailBot
from modmail.log import ModmailLogger
from modmail.utils import responses
from modmail.utils.cogs import BotModeEnum, ExtMetadata, ModmailCog
from modmail.utils.extensions import BOT_MODE, EXTENSIONS, NO_UNLOAD, ModuleDict, unqualify, walk_extensions
from modmail.utils.pagination import ButtonPaginator


log: ModmailLogger = logging.getLogger(__name__)


EXT_METADATA = ExtMetadata(load_if_mode=BotModeEnum.DEVELOP, no_unload=True)


class StatusEmojis:
    """Status emojis for extension statuses."""

    fully_loaded: str = ":green_circle:"
    partially_loaded: str = ":yellow_circle:"
    unloaded: str = ":red_circle:"
    disabled: str = ":brown_circle:"
    unknown: str = ":black_circle:"


Emojis = modmail.config.config().user.emojis


class Action(Enum):
    """Represents an action to perform on an extension."""

    # Need to be partial otherwise they are considered to be function definitions.
    LOAD = functools.partial(ModmailBot.load_extension)
    UNLOAD = functools.partial(ModmailBot.unload_extension)
    RELOAD = functools.partial(ModmailBot.reload_extension)

    # for plugins
    ENABLE = functools.partial(ModmailBot.load_extension)
    DISABLE = functools.partial(ModmailBot.unload_extension)

    INSTALL = functools.partial(ModmailBot.reload_extension)


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
            raise commands.BadArgument(f"{Emojis.failure} Could not find the {self.type} `{argument}`.")

        if len(matches) > 1:
            names = "\n".join(sorted(matches))
            raise commands.BadArgument(
                f"{Emojis.failure} `{argument}` is an ambiguous {self.type} name. "
                f"Please use one of the following fully-qualified names.```\n{names}```"
            )

        return matches[0]


class ExtensionManager(ModmailCog, name="Extension Manager"):
    """
    Extension management.

    Commands to load, reload, unload, and list extensions.
    """

    type = "extension"
    module_name = "extensions"  # modmail/extensions
    all_extensions: ModuleDict

    def __init__(self, bot: ModmailBot):
        self.bot = bot
        self.all_extensions = EXTENSIONS

    def get_black_listed_extensions(self) -> list:
        """Returns a list of all unload blacklisted extensions."""
        return NO_UNLOAD

    @commands.group("ext", aliases=("extensions", "exts"), invoke_without_command=True)
    async def extensions_group(self, ctx: Context) -> None:
        """Load, unload, reload, and list loaded extensions."""
        await ctx.send_help(ctx.command)

    @extensions_group.command(name="load", aliases=("l",), require_var_positional=True)
    async def load_extensions(self, ctx: Context, *extensions: ExtensionConverter) -> None:
        r"""
        Load extensions given their fully qualified or unqualified names.

        If '\*' is given as the name, all unloaded extensions will be loaded.
        """
        if "*" in extensions:
            extensions = sorted(ext for ext in self.all_extensions if ext not in self.bot.extensions.keys())

        msg, is_error = self.batch_manage(Action.LOAD, *extensions)
        if not is_error:
            await responses.send_positive_response(ctx, msg)
        else:
            await responses.send_negatory_response(ctx, msg)

    @extensions_group.command(name="unload", aliases=("ul",), require_var_positional=True)
    async def unload_extensions(self, ctx: Context, *extensions: ExtensionConverter) -> None:
        r"""
        Unload currently loaded extensions given their fully qualified or unqualified names.

        If '\*' is given as the name, all loaded extensions will be unloaded.
        """
        blacklisted = [ext for ext in self.get_black_listed_extensions() if ext in extensions]

        if blacklisted:
            bl_msg = "\n".join(blacklisted)
            await responses.send_negatory_response(
                ctx, f"{Emojis.failure} The following {self.type}(s) may not be unloaded:```\n{bl_msg}```"
            )
            return

        if "*" in extensions:
            extensions = sorted(
                ext
                for ext in self.bot.extensions.keys() & self.all_extensions
                if ext not in (self.get_black_listed_extensions())
            )

        msg, is_error = self.batch_manage(Action.UNLOAD, *extensions)
        if not is_error:
            await responses.send_positive_response(ctx, msg)
        else:
            await responses.send_negatory_response(ctx, msg)

    @extensions_group.command(name="reload", aliases=("r", "rl"), require_var_positional=True)
    async def reload_extensions(self, ctx: Context, *extensions: ExtensionConverter) -> None:
        r"""
        Reload extensions given their fully qualified or unqualified names.

        If an extension fails to be reloaded, it will be rolled-back to the prior working state.

        If '\*' is given as the name, all currently loaded extensions will be reloaded.
        """
        if "*" in extensions:
            extensions = self.bot.extensions.keys() & self.all_extensions

        msg, is_error = self.batch_manage(Action.RELOAD, *extensions)
        if not is_error:
            await responses.send_positive_response(ctx, msg)
        else:
            await responses.send_negatory_response(ctx, msg)

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
            log.trace(f"Extensions in category {category}: {extensions}")
            category = category.replace("_", " ").title()
            extensions = "\n".join(sorted(extensions))
            lines.append(f"**{category}**\n{extensions}\n")

        log.debug(f"{ctx.author} requested a list of all {self.type}s. " "Returning a paginated list.")

        await ButtonPaginator.paginate(
            lines or f"There are no {self.type}s installed.", ctx.message, embed=embed
        )

    def _resync_extensions(self) -> None:
        """Resyncs extensions. Useful for when the files are dynamically updated."""
        log.debug(f"Refreshing list of {self.type}s.")

        # make sure the new walk contains all currently loaded extensions, so they can be unloaded
        all_exts: ModuleDict = {}
        for name, metadata in self.all_extensions.items():
            if name in self.bot.extensions:
                all_exts[name] = metadata

        # re-walk the extensions
        for name, metadata in walk_extensions():
            all_exts[name] = metadata

        self.all_extensions.clear()
        self.all_extensions.update(all_exts)

    @extensions_group.command(name="refresh", aliases=("rewalk", "rescan"))
    async def resync_extensions(self, ctx: Context) -> None:
        """
        Refreshes the list of extensions from disk, but do not unload any currently active.

        Typical use case is in the event that the existing extensions have changed while the bot is running.
        """
        self._resync_extensions()
        await responses.send_positive_response(ctx, f":ok_hand: Refreshed list of {self.type}s.")

    def group_extension_statuses(self) -> Mapping[str, str]:
        """Return a mapping of extension names and statuses to their categories."""
        categories = defaultdict(list)

        for ext, metadata in self.all_extensions.items():
            if ext in self.bot.extensions:
                status = StatusEmojis.fully_loaded
            elif metadata.load_if_mode & BOT_MODE:
                status = StatusEmojis.disabled
            else:
                status = StatusEmojis.unloaded

            root, name = ext.rsplit(".", 1)
            if root.split(".", 1)[1] == self.module_name:
                category = f"General {self.type}s"
            else:
                category = " - ".join(root.split(".")[2:])
            categories[category].append(f"{status}  {name}")

        return dict(categories)

    def batch_manage(
        self,
        action: Action,
        *extensions: str,
        **kw,
    ) -> Tuple[str, bool]:
        """
        Apply an action to multiple extensions and return a message with the results.

        Any extra kwargs are passed to `manage()` which handles all passed modules.
        """
        if len(extensions) == 1:
            msg, failures = self.manage(action, extensions[0], **kw)
            return msg, bool(failures)

        verb = action.name.lower()
        failures = {}

        for extension in sorted(extensions):
            _, error = self.manage(action, extension, **kw)
            if error:
                failures[extension] = error

        emoji = Emojis.failure if failures else Emojis.success
        msg = f"{emoji} {len(extensions) - len(failures)} / {len(extensions)} {self.type}s {verb}ed."

        if failures:
            failures = "\n".join(f"{ext}\n    {err}" for ext, err in failures.items())
            msg += f"\nFailures:```\n{failures}```"

        log.debug(f"Batch {verb}ed {self.type}s.")

        return msg, bool(failures)

    def manage(
        self,
        action: Action,
        ext: str,
        *,
        is_plugin: bool = False,
        suppress_already_error: bool = False,
    ) -> Tuple[str, Union[str, bool]]:
        """Apply an action to an extension and return the status message and any error message."""
        verb = action.name.lower()
        error_msg = None
        msg = None
        not_quite = False
        try:
            action.value(self.bot, ext)
        except (commands.ExtensionAlreadyLoaded, commands.ExtensionNotLoaded):
            if suppress_already_error:
                pass
            elif action is Action.RELOAD:
                # When reloading, have a special error.
                msg = (
                    f"{Emojis.failure} {self.type.capitalize()} "
                    f"`{ext}` is not loaded, so it was not {verb}ed."
                )
                not_quite = True
            elif action is Action.INSTALL:
                # extension wasn't loaded, so load it
                # this is used for plugins
                Action.LOAD.value(self.bot, ext)

            else:
                msg = f"{Emojis.failure} {self.type.capitalize()} `{ext}` is already {verb.rstrip('e')}ed."
                not_quite = True
        except Exception as e:
            if hasattr(e, "original"):
                # If original exception is present, then utilize it
                e = e.original

            log.exception(f"{self.type.capitalize()} '{ext}' failed to {verb}.")

            error_msg = f"{e.__class__.__name__}: {e}"
            msg = f"{Emojis.failure} Failed to {verb} {self.type} `{ext}`:\n```\n{error_msg}```"

        if msg is None:
            msg = f"{Emojis.success} {self.type.capitalize()} successfully {verb.rstrip('e')}ed: `{ext}`."

        log.debug(error_msg or msg)
        return msg, error_msg or not_quite

    # This cannot be static (must have a __func__ attribute).
    async def cog_check(self, ctx: Context) -> bool:
        """Only allow bot owners to invoke the commands in this cog."""
        # TODO: Change to allow other users to invoke this too.
        return await self.bot.is_owner(ctx.author)

    # This cannot be static (must have a __func__ attribute).
    async def cog_command_error(self, ctx: Context, error: Exception) -> None:
        """Handle BadArgument errors locally to prevent the help command from showing."""
        if isinstance(error, commands.BadArgument):
            await responses.send_negatory_response(ctx, str(error))
            error.handled = True
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send_help(ctx.command)
        else:
            raise error


def setup(bot: ModmailBot) -> None:
    """Load the Extension Manager cog."""
    bot.add_cog(ExtensionManager(bot))
