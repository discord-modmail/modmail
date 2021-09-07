from __future__ import annotations

import asyncio
import logging
import shutil
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List, Mapping

from discord import Colour, Embed
from discord.ext import commands
from discord.ext.commands import Context

import modmail.addons.utils as addon_utils
from modmail import errors
from modmail.addons.converters import SourceAndPluginConverter
from modmail.addons.errors import PluginNotFoundError
from modmail.addons.models import AddonSource, Plugin, SourceTypeEnum
from modmail.addons.plugins import BASE_PLUGIN_PATH, PLUGINS, find_plugins_in_dir, walk_plugin_files
from modmail.extensions.extension_manager import Action, ExtensionConverter, ExtensionManager
from modmail.utils.cogs import BotModeEnum, ExtMetadata
from modmail.utils.extensions import BOT_MODE
from modmail.utils.pagination import ButtonPaginator


if TYPE_CHECKING:
    from modmail.bot import ModmailBot
    from modmail.log import ModmailLogger

EXT_METADATA = ExtMetadata(load_if_mode=BotModeEnum.PRODUCTION, no_unload=True)

logger: ModmailLogger = logging.getLogger(__name__)

PLUGIN_DEV_ENABLED = BOT_MODE & BotModeEnum.PLUGIN_DEV


class PluginDevPathConverter(ExtensionConverter):
    """
    Fully qualify the name of a plugin and ensure it exists.

    The * value bypasses this when used with a plugin manager command.
    """

    source_list = PLUGINS
    type = "plugin"
    NO_UNLOAD = None


class PluginConverter(commands.Converter):
    """Convert a plugin name into a full plugin with path and related args."""

    async def convert(self, ctx: Context, argument: str) -> List[str]:
        """Converts a plugin into a full plugin with a path and all other attributes."""
        loaded_plugs: Dict[Plugin, List[str]] = ctx.bot.installed_plugins

        for plug in loaded_plugs:
            if argument in (plug.name, plug.folder_name):
                return plug

        raise commands.BadArgument(f"{argument} is not in list of installed plugins.")


class PluginFilesConverter(commands.Converter):
    """
    Convert a name of a plugin into a full plugin.

    In this case Plugins are group of extensions, as if they have multiple files in their directory,
    they will be treated as one plugin for the sake of managing.
    """

    async def convert(self, ctx: Context, argument: str) -> List[str]:
        """Converts a provided plugin into a list of its paths."""
        loaded_plugs: Dict[Plugin, List[str]] = ctx.bot.installed_plugins

        for plug in loaded_plugs:
            if argument in (plug.name, plug.folder_name):
                return loaded_plugs[plug]

        raise commands.BadArgument(f"{argument} is not an installed plugin.")


class PluginManager(ExtensionManager, name="Plugin Manager"):
    """Plugin management commands."""

    type = "plugin"
    module_name = "plugins"  # modmail/plugins

    def __init__(self, bot: ModmailBot):
        super().__init__(bot)
        self.all_extensions = PLUGINS
        self.refresh_method = walk_plugin_files

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

    @plugins_group.group(
        "dev", aliases=("developer", "d"), invoke_without_command=True, enabled=PLUGIN_DEV_ENABLED
    )
    async def plugin_dev_group(self, ctx: Context) -> None:
        """Manage plugin files directly, rather than whole plugin objects."""
        await ctx.send_help(ctx.command)

    @plugin_dev_group.command(name="load", aliases=("l",))
    async def load_plugins(self, ctx: Context, *plugins: PluginDevPathConverter) -> None:
        r"""
        Load plugins given their fully qualified or unqualified names.

        If '\*' is given as the name, all unloaded plugins will be loaded.
        """
        await self.load_extensions.callback(self, ctx, *plugins)

    @plugin_dev_group.command(name="unload", aliases=("ul",))
    async def unload_plugins(self, ctx: Context, *plugins: PluginDevPathConverter) -> None:
        r"""
        Unload currently loaded plugins given their fully qualified or unqualified names.

        If '\*' is given as the name, all loaded plugins will be unloaded.
        """
        await self.unload_extensions.callback(self, ctx, *plugins)

    @plugin_dev_group.command(name="reload", aliases=("r", "rl"))
    async def reload_plugins(self, ctx: Context, *plugins: PluginDevPathConverter) -> None:
        r"""
        Reload plugins given their fully qualified or unqualified names.

        If an plugin fails to be reloaded, it will be rolled-back to the prior working state.

        If '\*' is given as the name, all currently loaded plugins will be reloaded.
        """
        await self.reload_extensions.callback(self, ctx, *plugins)

    @plugin_dev_group.command(name="list", aliases=("all", "ls"))
    async def dev_list_plugins(self, ctx: Context) -> None:
        """
        Get a list of all plugin files, including their loaded status.

        Red indicates that the plugin file is unloaded.
        Green indicates that the plugin file is currently loaded.
        """
        await self.list_extensions.callback(self, ctx)

    @plugin_dev_group.command(name="refresh", aliases=("rewalk", "rescan"))
    async def resync_plugins(self, ctx: Context) -> None:
        """Refreshes the list of plugins from disk, but do not unload any currently active."""
        await self.resync_extensions.callback(self, ctx)

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
        logger.debug(f"Received command to download plugin {plugin.name} from https://{source.zip_url}")
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
            # check if user-provided plugin matches either plugin name or folder name
            if plugin.name in (p.name, p.folder_name):
                install_path = BASE_PLUGIN_PATH / p.folder_path.name
                try:
                    shutil.copytree(p.folder_path, install_path, dirs_exist_ok=True)
                except FileExistsError:
                    await ctx.send(
                        "Plugin already seems to be installed. "
                        "This could be caused by the plugin already existing, "
                        "or a plugin of the same name existing."
                    )
                    return
                p.installed_path = install_path
                plugin = p
                break

        if plugin.folder_path is None:
            raise PluginNotFoundError(f"Could not find plugin {plugin}")
        logger.trace(f"{BASE_PLUGIN_PATH = }")

        PLUGINS.update(walk_plugin_files(BASE_PLUGIN_PATH / p.folder_path.name))

        files_to_load: List[str] = []
        for plug in plugins[plugin]:
            logger.trace(f"{plug = }")
            try:
                plug = await PluginDevPathConverter().convert(None, plug.name.rstrip(".py"))
            except commands.BadArgument:
                pass
            else:
                if plug in PLUGINS:
                    files_to_load.append(plug)

        logger.debug(f"{files_to_load = }")
        self.batch_manage(Action.LOAD, *files_to_load)

        self.bot.installed_plugins[plugin] = files_to_load

        await ctx.reply(f"Installed plugin {plugin.name}.")

    @plugins_group.command(name="uninstall", aliases=("rm",))
    async def uninstall_plugin(self, ctx: Context, *, plugin: PluginConverter) -> None:
        """Uninstall a provided plugin, given the name of the plugin."""
        plugin: Plugin = plugin

        # plugin_files: List[str] = await PluginFilesConverter().convert(ctx, plugin.folder_name)
        await self.disable_plugin.callback(self, ctx, plugin=plugin)

        shutil.rmtree(plugin.installed_path)

        plugin_files: List[str] = await PluginFilesConverter().convert(ctx, plugin.folder_name)
        for file_ in plugin_files:
            del PLUGINS[file_]
        del self.bot.installed_plugins[plugin]

        await ctx.send(plugin.installed_path)

    @plugins_group.command(name="enable")
    async def enable_plugin(self, ctx: Context, *, plugin: PluginConverter) -> None:
        """Enable a provided plugin, given the name or folder of the plugin."""
        plugin: Plugin = plugin

        plugin_files: List[str] = await PluginFilesConverter().convert(ctx, plugin.folder_name)

        await self.load_plugins.callback(self, ctx, *plugin_files)

    @plugins_group.command(name="disable")
    async def disable_plugin(self, ctx: Context, *, plugin: PluginConverter) -> None:
        """Disable a provided plugin, given the name or folder of the plugin."""
        plugin: Plugin = plugin

        plugin_files: List[str] = await PluginFilesConverter().convert(ctx, plugin.folder_name)

        await self.unload_plugins.callback(self, ctx, *plugin_files)

    def group_plugin_statuses(self) -> Mapping[str, str]:
        """Return a mapping of plugin names and statuses to their module."""
        plugins = defaultdict(str)

        for plug, files in self.bot.installed_plugins.items():
            plug_status = []
            for ext in files:
                if ext in self.bot.extensions:
                    status = True
                else:
                    status = False
                plug_status.append(status)

            if all(plug_status):
                status = ":green_circle:"
            elif any(plug_status):
                status = ":yellow_circle:"
            else:
                status = ":red_circle:"

            plugins[plug.name] = status

        return dict(plugins)

    @plugins_group.command(name="list", aliases=("all", "ls"))
    async def list_plugins(self, ctx: Context) -> None:
        """
        Get a list of all plugins, including their loaded status.

        Green indicates that the extension is fully loaded.
        Yellow indicates that the plugin is partially loaded.
        Red indicates that the plugin is fully unloaded.
        """
        embed = Embed(colour=Colour.blurple())
        embed.set_author(
            name=f"{self.type.capitalize()} List",
        )

        lines = []
        plugin_statuses = self.group_plugin_statuses()
        for plugin_name, status in sorted(plugin_statuses.items()):
            # plugin_name = plugin_name.replace("_", " ").title()
            lines.append(f"{status}  **{plugin_name}**")

        logger.debug(f"{ctx.author} requested a list of all {self.type}s. " "Returning a paginated list.")

        await ButtonPaginator.paginate(
            lines or f"There are no {self.type}s installed.", ctx.message, embed=embed
        )

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
