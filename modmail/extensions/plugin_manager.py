from __future__ import annotations

import asyncio
import logging
import zipfile
from typing import TYPE_CHECKING

from discord.ext import commands
from discord.ext.commands import Context

import modmail.addons.utils as addon_utils
from modmail import errors
from modmail.addons.converters import SourceAndPluginConverter
from modmail.addons.models import AddonSource, Plugin, SourceTypeEnum
from modmail.addons.plugins import BASE_PATH, PLUGINS, find_plugins_in_zip, walk_plugins
from modmail.extensions.extension_manager import Action, ExtensionConverter, ExtensionManager
from modmail.utils.cogs import BotModes, ExtMetadata

if TYPE_CHECKING:
    from modmail.bot import ModmailBot
    from modmail.log import ModmailLogger

EXT_METADATA = ExtMetadata(load_if_mode=BotModes.PRODUCTION)

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
        plugin: Plugin
        source: AddonSource
        plugin, source = source_and_plugin
        if source.source_type is SourceTypeEnum.LOCAL:
            # TODO: check the path of a local plugin
            await ctx.send("This plugin is a local plugin, and likely can be loaded with the load command.")
            return
        logger.debug(f"Received command to download plugin {plugin.name} from {source.zip_url}")
        try:
            file = await addon_utils.download_zip_from_source(source, self.bot.http_session)
        except errors.HTTPError:
            await ctx.send(f"Downloading {source.zip_url} did not give a 200 response code.")
            return
        else:
            file = zipfile.ZipFile(file.filename)
            await ctx.send(f"Downloaded {file.filename}")

        temp_direct_children = [p for p in zipfile.Path(file).iterdir()]
        if len(temp_direct_children) == 1:
            folder = temp_direct_children[0]
            if folder.is_dir():
                addon_utils.move_zip_contents_up_a_level(file.filename, temp_direct_children)
                file.close()
                file = zipfile.ZipFile(file.filename)

        # determine plugins in the archive
        top_level_plugins, all_plugin_files = find_plugins_in_zip(file.filename)

        # yield to any coroutines that need to run
        await asyncio.sleep(0)

        # extract the drive
        file.extractall(BASE_PATH / source.addon_directory, all_plugin_files)

        # TODO: rewrite this as it only needs to (and should) scan the new directory
        self._resync_extensions()

        temp_new_plugins = [x.strip("/").rsplit("/", 1)[1] for x in all_plugin_files]
        new_plugins = []
        for p in temp_new_plugins:
            logger.debug(p)
            try:
                new_plugins.append(await PluginPathConverter().convert(None, p))
            except commands.BadArgument:
                pass

        self.batch_manage(Action.LOAD, *new_plugins)
        await ctx.reply("Installed plugins: \n" + "\n".join(top_level_plugins))

    # TODO: Implement install/enable/disable/etc

    # This cannot be static (must have a __func__ attribute).
    async def cog_check(self, ctx: Context) -> bool:
        """Only allow server admins and bot owners to invoke the commands in this cog."""
        if ctx.guild is None:
            return await self.bot.is_owner(ctx.author)
        else:
            return ctx.author.guild_permissions.administrator or await self.bot.is_owner(ctx.author)


# HACK: Delete the commands from ExtensionManager that PluginManager has inherited
# before discord.py tries to re-register them
for command in ExtensionManager.__cog_commands__:
    PluginManager.__cog_commands__.remove(command)


def setup(bot: ModmailBot) -> None:
    """Load the Plugins Manager cog."""
    # PluginManager includes the ExtensionManager
    bot.add_cog(PluginManager(bot))
