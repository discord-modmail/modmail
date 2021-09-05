from __future__ import annotations

import asyncio
import logging
import shutil
from typing import TYPE_CHECKING, List

from discord.ext import commands
from discord.ext.commands import Context

import modmail.addons.utils as addon_utils
from modmail import errors
from modmail.addons.converters import SourceAndPluginConverter
from modmail.addons.errors import PluginNotFoundError
from modmail.addons.models import AddonSource, Plugin, SourceTypeEnum
from modmail.addons.plugins import BASE_PLUGIN_PATH, PLUGINS, find_plugins_in_dir, walk_plugins
from modmail.extensions.extension_manager import Action, ExtensionConverter, ExtensionManager
from modmail.utils.cogs import BotModes, ExtMetadata


if TYPE_CHECKING:
    from modmail.bot import ModmailBot
    from modmail.log import ModmailLogger

EXT_METADATA = ExtMetadata(load_if_mode=BotModes.PRODUCTION, no_unload=True)

logger: ModmailLogger = logging.getLogger(__name__)


class PluginPathConverter(ExtensionConverter):
    """
    Fully qualify the name of a plugin and ensure it exists.

    The * value bypasses this when used with a plugin manager command.
    """

    source_list = PLUGINS
    type = "plugin"
    NO_UNLOAD = None


class PluginManager(ExtensionManager, name="Plugin Manager"):
    """Plugin management commands."""

    type = "plugin"
    module_name = "plugins"  # modmail/plugins

    def __init__(self, bot: ModmailBot):
        super().__init__(bot)
        self.all_extensions = PLUGINS
        self.refresh_method = walk_plugins

    def get_black_listed_extensions(self) -> list:
        """
        Returns a list of all unload blacklisted plugins.

        This method exists to override the one in extensions manager,
        due to the fact that blacklisting plugins is not supported.
        """
        return []

    @commands.group("plugins", aliases=("plug", "plugs"), invoke_without_command=True)
    async def plugins_group(self, ctx: Context) -> None:
        """Install, uninstall, disable, update, and enable installed plugins."""
        await ctx.send_help(ctx.command)

    @plugins_group.command(name="load", aliases=("l",))
    async def load_plugin(self, ctx: Context, *plugins: PluginPathConverter) -> None:
        r"""
        Load plugins given their fully qualified or unqualified names.

        If '\*' is given as the name, all unloaded plugins will be loaded.
        """
        await self.load_extensions.callback(self, ctx, *plugins)

    @plugins_group.command(name="unload", aliases=("ul",))
    async def unload_plugins(self, ctx: Context, *plugins: PluginPathConverter) -> None:
        r"""
        Unload currently loaded plugins given their fully qualified or unqualified names.

        If '\*' is given as the name, all loaded plugins will be unloaded.
        """
        await self.unload_extensions.callback(self, ctx, *plugins)

    @plugins_group.command(name="reload", aliases=("r", "rl"))
    async def reload_plugins(self, ctx: Context, *plugins: PluginPathConverter) -> None:
        r"""
        Reload plugins given their fully qualified or unqualified names.

        If an plugin fails to be reloaded, it will be rolled-back to the prior working state.

        If '\*' is given as the name, all currently loaded plugins will be reloaded.
        """
        await self.reload_extensions.callback(self, ctx, *plugins)

    @plugins_group.command(name="list", aliases=("all", "ls"))
    async def list_plugins(self, ctx: Context) -> None:
        """
        Get a list of all plugins, including their loaded status.

        Red indicates that the plugin is unloaded.
        Green indicates that the plugin is currently loaded.
        """
        await self.list_extensions.callback(self, ctx)

    @plugins_group.command(name="refresh", aliases=("rewalk", "rescan"))
    async def resync_plugins(self, ctx: Context) -> None:
        """Refreshes the list of plugins from disk, but do not unload any currently active."""
        await self.resync_extensions.callback(self, ctx)

    @plugins_group.command("convert", hidden=True)
    async def plugin_convert_test(self, ctx: Context, *, plugin: SourceAndPluginConverter) -> None:
        """Convert a plugin and given its source information."""
        await ctx.send(f"```py\n{plugin.__repr__()}```")

    @plugins_group.command(name="install", aliases=("",))
    async def install_plugins(self, ctx: Context, *, source_and_plugin: SourceAndPluginConverter) -> None:
        """Install plugins from provided repo."""
        # this could take a while
        await ctx.trigger_typing()

        # create variables for the user input, typehint them, then assign them from the converter tuple
        plugin: Plugin
        source: AddonSource
        plugin, source = source_and_plugin

        if source.source_type is SourceTypeEnum.LOCAL:
            # TODO: check the path of a local plugin
            await ctx.send("This plugin is a local plugin, and likely can be loaded with the load command.")
            return
        logger.debug(f"Received command to download plugin {plugin.name} from {source.zip_url}")
        try:
            directory = await addon_utils.download_and_unpack_source(source, self.bot.http_session)
        except errors.HTTPError:
            await ctx.send(f"Downloading {source.zip_url} did not give a 200 response code.")
            return

        source.cache_file = directory

        # determine plugins in the archive
        plugins = find_plugins_in_dir(directory)

        # yield to any coroutines that need to run
        # its not possible to do this with aiofiles, so when we export the zip,
        # its important to yield right after
        await asyncio.sleep(0)

        # copy the requested plugin over to the new folder
        for p in plugins.keys():
            if p.name == plugin.name:
                try:
                    shutil.copytree(p.folder_path, BASE_PLUGIN_PATH / p.folder_path.name, dirs_exist_ok=True)
                except FileExistsError:
                    await ctx.send(
                        "Plugin already seems to be installed. "
                        "This could be caused by the plugin already existing, "
                        "or a plugin of the same name existing."
                    )
                    return
                plugin = p
                break

        if plugin.folder_path is None:
            raise PluginNotFoundError(f"Could not find plugin {plugin}")
        logger.trace(f"{BASE_PLUGIN_PATH = }")

        # TODO: rewrite this method as it only needs to (and should) scan the new directory
        self._resync_extensions()
        files_to_load: List[str] = []
        for plug in plugins[plugin]:
            logger.trace(f"{plug = }")
            try:
                plug = await PluginPathConverter().convert(None, plug.name.rstrip(".py"))
            except commands.BadArgument:
                pass
            else:
                if plug in PLUGINS:
                    files_to_load.append(plug)

        logger.debug(f"{files_to_load = }")
        self.batch_manage(Action.LOAD, *files_to_load)

        await ctx.reply(f"Installed plugin {plugin.name}.")

    # TODO: Implement enable/disable/etc

    # This cannot be static (must have a __func__ attribute).
    async def cog_check(self, ctx: Context) -> bool:
        """Only allow server admins and bot owners to invoke the commands in this cog."""
        if ctx.guild is None:
            return await self.bot.is_owner(ctx.author)
        else:
            return await self.bot.is_owner(ctx.author)


# HACK: Delete the commands from ExtensionManager that PluginManager has inherited
# before discord.py tries to re-register them
for command in ExtensionManager.__cog_commands__:
    PluginManager.__cog_commands__.remove(command)


def setup(bot: ModmailBot) -> None:
    """Load the Plugins Manager cog."""
    # PluginManager includes the ExtensionManager
    bot.add_cog(PluginManager(bot))
