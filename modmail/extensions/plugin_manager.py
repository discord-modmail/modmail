from __future__ import annotations

import asyncio
import logging
import shutil
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, Mapping, Set

from atoml.exceptions import ParseError
from discord import Colour, Embed
from discord.abc import Messageable
from discord.ext import commands
from discord.ext.commands import Context
from rapidfuzz import fuzz, process

import modmail.addons.utils as addon_utils
from modmail import errors
from modmail.addons.converters import SourceAndPluginConverter
from modmail.addons.errors import NoPluginTomlFoundError
from modmail.addons.models import AddonSource, Plugin, SourceTypeEnum
from modmail.addons.plugins import (
    BASE_PLUGIN_PATH,
    PLUGINS,
    find_partial_plugins_from_dir,
    find_plugins,
    update_local_toml_enable_or_disable,
    walk_plugin_files,
)
from modmail.extensions.extension_manager import Action, ExtensionConverter, ExtensionManager, StatusEmojis
from modmail.utils import responses
from modmail.utils.cogs import BotModeEnum, ExtMetadata
from modmail.utils.extensions import BOT_MODE, ModuleDict
from modmail.utils.pagination import ButtonPaginator


if TYPE_CHECKING:
    from modmail.bot import ModmailBot
    from modmail.log import ModmailLogger

EXT_METADATA = ExtMetadata(no_unload=True)

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

    def __init__(self):
        """Properly set the source_list."""
        super().__init__()
        PluginDevPathConverter.source_list
        modules: ModuleDict = {}
        for plug in PluginDevPathConverter.source_list:
            modules.update({k: v for k, v in plug.modules.items()})
        self.source_list = modules


class PluginConverter(commands.Converter):
    """Convert a plugin name into a full plugin with path and related args."""

    async def convert(self, ctx: Context, argument: str) -> Plugin:
        """Converts a plugin into a full plugin with a path and all other attributes."""
        loaded_plugs: Set[Plugin] = PLUGINS

        # its possible to have a plugin with the same name as a folder of a plugin
        # folder names are the priority
        secondary_names = dict()
        for plug in loaded_plugs:
            if argument == plug.name:
                return plug
            secondary_names[plug.folder_name] = plug

        if argument in secondary_names:
            return secondary_names[argument]

        # Determine close plugins
        # Using a set to prevent duplicates
        # all_possible_args: Set[str] = set()
        arg_mapping: Dict[str, Plugin] = dict()
        for plug in loaded_plugs:
            for name in plug.name, plug.folder_name:
                # all_possible_args.add(name)
                arg_mapping[name] = plug

        result = process.extract(
            argument,
            arg_mapping.keys(),
            scorer=fuzz.ratio,
            score_cutoff=86,
        )
        logger.debug(f"{result = }")

        if not len(result):
            raise commands.BadArgument(f"`{argument}` is not in list of installed plugins.")

        all_fully_matched_plugins: Set[Plugin] = set()
        all_partially_matched_plugins: Dict[Plugin, float] = dict()
        for res in result:
            all_partially_matched_plugins[arg_mapping[res[0]]] = res[1]

            if res[1] == 100:
                all_fully_matched_plugins.add(arg_mapping[res[0]])

        if len(all_fully_matched_plugins) != 1:
            suggested = ""
            for plug, percent in all_partially_matched_plugins.items():
                suggested += f"`{plug.name}` ({round(percent)}%)\n"
            raise commands.BadArgument(
                f"`{argument}` is not in list of installed plugins."
                f"\n\n**Suggested plugins**:\n{suggested}"
                if len(suggested)
                else ""
            )

        return await self.convert(ctx, all_fully_matched_plugins.pop().name)


class PluginManager(ExtensionManager, name="Plugin Manager"):
    """Plugin management commands."""

    type = "plugin"
    module_name = "plugins"  # modmail/plugins

    def __init__(self, bot: ModmailBot):
        super().__init__(bot)

        modules: ModuleDict = {}
        for plug in PLUGINS:
            modules.update({k: v for k, v in plug.modules.items()})
        self.all_extensions = modules

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
        "dev", aliases=("developer",), invoke_without_command=True, enabled=PLUGIN_DEV_ENABLED
    )
    async def plugin_dev_group(self, ctx: Context) -> None:
        """Manage plugin files directly, rather than whole plugin objects."""
        await ctx.send_help(ctx.command)

    @plugin_dev_group.command(name="load", aliases=("l",))
    async def load_plugins(self, ctx: Context, *plugins: PluginDevPathConverter) -> None:
        r"""
        Load singular plugin files given their fully qualified or unqualified names.

        If '\*' is given as the name, all unloaded plugins will be loaded.
        """
        await self.load_extensions.callback(self, ctx, *plugins)

    @plugin_dev_group.command(name="unload", aliases=("u", "ul"))
    async def unload_plugins(self, ctx: Context, *plugins: PluginDevPathConverter) -> None:
        r"""
        Unoad singular plugin files given their fully qualified or unqualified names.

        If '\*' is given as the name, all loaded plugins will be unloaded.
        """
        await self.unload_extensions.callback(self, ctx, *plugins)

    @plugin_dev_group.command(name="reload", aliases=("r", "rl"))
    async def reload_plugins(self, ctx: Context, *plugins: PluginDevPathConverter) -> None:
        r"""
        Reload singular plugin files given their fully qualified or unqualified names.

        If a plugin file fails to be reloaded, it will be rolled-back to the prior working state.

        If '\*' is given as the name, all currently loaded plugins will be reloaded.
        """
        await self.reload_extensions.callback(self, ctx, *plugins)

    def group_extension_statuses(self) -> Mapping[str, str]:
        """Return a mapping of plugin names and statuses to their categories."""
        categories = defaultdict(list)

        for plug in PLUGINS:
            for mod, metadata in plug.modules.items():
                if mod in self.bot.extensions:
                    status = StatusEmojis.fully_loaded
                elif metadata.load_if_mode & BOT_MODE:
                    status = StatusEmojis.disabled
                else:
                    status = StatusEmojis.unloaded

                name = mod.split(".", 2)[-1]
                categories[plug.name].append(f"{status}  `{name}`")

        return dict(categories)

    def _resync_extensions(self) -> None:
        """Resyncs plugin. Useful for when the files are dynamically updated."""
        logger.debug(f"Refreshing list of {self.type}s.")

        # remove all fully unloaded plugins from the list
        for plug in PLUGINS:
            safe_to_remove = []
            for mod in plug.modules:
                safe_to_remove.append(mod not in self.bot.extensions)
            if all(safe_to_remove):
                PLUGINS.remove(plug)

        for plug in find_plugins():
            PLUGINS.update(plug)

        modules: ModuleDict = {}
        for plug in PLUGINS:
            modules.update({k: v for k, v in plug.modules.items()})
        self.all_extensions = modules

    @plugin_dev_group.command(name="refresh", aliases=("rewalk", "rescan", "resync"))
    async def resync_plugins(self, ctx: Context) -> None:
        """Refreshes the list of plugins from disk, but do not unload any currently active."""
        await self.resync_extensions.callback(self, ctx)

    @commands.max_concurrency(1, per=commands.BucketType.default, wait=True)
    @plugins_group.command(name="install", aliases=("add",))
    async def install_plugins(self, ctx: Context, *, source_and_plugin: SourceAndPluginConverter) -> None:
        """Install plugins from provided repo."""
        # this could take a while
        # I'm aware this should be a context manager, but do not want to indent almost the entire command
        await ctx.trigger_typing()

        # create variables for the user input, typehint them, then assign them from the converter tuple
        plugin: Plugin
        source: AddonSource
        plugin, source = source_and_plugin

        if source.source_type is SourceTypeEnum.LOCAL:
            # TODO: check the path of a local plugin
            await responses.send_negatory_response(
                ctx,
                "This plugin seems to be a local plugin, and therefore can probably be "
                "loaded with the load command, if it isn't loaded already.",
            )
            return
        logger.debug(f"Received command to download plugin {plugin.name} from https://{source.zip_url}")
        try:
            directory = await addon_utils.download_and_unpack_source(source, self.bot.http_session)
        except errors.HTTPError:
            await responses.send_negatory_response(
                ctx, f"Downloading {source.zip_url} did not give a 200 response code."
            )
            return

        source.cache_file = directory

        # determine plugins in the archive
        archive_plugins = {x for x in find_partial_plugins_from_dir(directory)}

        # yield to any coroutines that need to run
        # afaik its not possible to do this with aiofiles, so when we export the zip,
        # its important to yield right after
        await asyncio.sleep(0)

        # copy the requested plugin over to the new folder
        for p in archive_plugins:
            # check if user-provided plugin matches either plugin name or folder name
            if plugin.name in (p.name, p.folder_name):
                install_path = BASE_PLUGIN_PATH / p.folder_path.name
                try:
                    shutil.copytree(p.folder_path, install_path, dirs_exist_ok=True)
                except FileExistsError:
                    await responses.send_negatory_response(
                        ctx,
                        "Plugin already seems to be installed. "
                        "This could be caused by the plugin already existing, "
                        "or a plugin of the same name existing.",
                    )
                    return
                p.installed_path = install_path
                plugin = p
                break

        if plugin.folder_path is None:
            await responses.send_negatory_response(ctx, f"Could not find plugin {plugin}")
            return
        logger.trace(f"{BASE_PLUGIN_PATH = }")

        plugin.modules.update(walk_plugin_files(BASE_PLUGIN_PATH / plugin.folder_name))

        PLUGINS.add(plugin)

        self.batch_manage(Action.LOAD, *plugin.modules.keys())

        await responses.send_positive_response(ctx, f"Installed plugin {plugin}.")

    @plugins_group.command(name="uninstall", aliases=("rm",))
    async def uninstall_plugin(self, ctx: Context, *, plugin: PluginConverter) -> None:
        """Uninstall a provided plugin, given the name of the plugin."""
        plugin: Plugin = plugin

        if plugin.local:
            await responses.send_negatory_response(
                ctx, "You may not uninstall a local plugin.\nUse the disable command to stop using it."
            )
            return

        plugin = await PluginConverter().convert(ctx, plugin.folder_name)
        _, err = self.batch_manage(
            Action.UNLOAD, *plugin.modules.keys(), is_plugin=True, suppress_already_error=True
        )
        if err:
            await responses.send_negatory_response(
                ctx, "There was a problem unloading the plugin from the bot."
            )
            return

        shutil.rmtree(plugin.installed_path)

        plugin = await PluginConverter().convert(ctx, plugin.folder_name)
        PLUGINS.remove(plugin)

        await responses.send_positive_response(ctx, f"Successfully uninstalled plugin {plugin}")

    async def _enable_or_disable_plugin(
        self,
        ctx: Messageable,
        plugin: Plugin,
        action: Action,
        enable: bool,
    ) -> None:
        """Enables or disables a provided plugin."""
        verb = action.name.lower()
        if plugin.enabled == enable:
            await responses.send_negatory_response(ctx, f"Plugin {plugin!s} is already {verb}d.")
            return

        plugin.enabled = enable

        if plugin.local:
            try:
                update_local_toml_enable_or_disable(plugin)
            except (NoPluginTomlFoundError, ParseError) as e:
                plugin.enabled = not plugin.enabled  # reverse the state
                await responses.send_negatory_response(ctx, e.args[0])

        msg, err = self.batch_manage(
            action, *plugin.modules.keys(), is_plugin=True, suppress_already_error=True
        )
        if err:
            await responses.send_negatory_response(
                ctx, "Er, something went wrong.\n" f":x: {plugin!s} was unable to be {verb}d properly!"
            )
        else:
            await responses.send_positive_response(ctx, f":thumbsup: Plugin {plugin!s} successfully {verb}d.")

    @plugins_group.command(name="enable")
    async def enable_plugin(self, ctx: Context, *, plugin: PluginConverter) -> None:
        """Enable a provided plugin, given the name or folder of the plugin."""
        await self._enable_or_disable_plugin(ctx, plugin, Action.ENABLE, True)

    @plugins_group.command(name="disable")
    async def disable_plugin(self, ctx: Context, *, plugin: PluginConverter) -> None:
        """Disable a provided plugin, given the name or folder of the plugin."""
        await self._enable_or_disable_plugin(ctx, plugin, Action.DISABLE, False)

    def group_plugin_statuses(self) -> Mapping[str, str]:
        """Return a mapping of plugin names and statuses to their module."""
        plugins = defaultdict(str)

        for plug in self.bot.installed_plugins:
            plug_status = []
            for mod, metadata in plug.modules.items():
                status = mod in self.bot.extensions
                # check that the file is supposed to be loaded
                if not status and not metadata.load_if_mode & self.bot.mode:
                    continue
                plug_status.append(status)

            if len(plug_status) == 0:
                status = StatusEmojis.unknown
            elif all(plug_status):
                status = StatusEmojis.fully_loaded
            elif any(plug_status):
                status = StatusEmojis.partially_loaded
            else:
                if plug.enabled:
                    status = StatusEmojis.unloaded
                else:
                    status = StatusEmojis.disabled

            plugins[plug.name] = status

        return dict(plugins)

    @plugins_group.group(name="list", aliases=("all", "ls"), invoke_without_command=True)
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
        if PLUGIN_DEV_ENABLED:
            kw = {"footer_text": "Tip: use the detailed command to see all plugin files"}
        else:
            kw = {}
        await ButtonPaginator.paginate(
            lines or f"There are no {self.type}s installed.", ctx.message, embed=embed, **kw
        )

    @list_plugins.command(name="detailed", aliases=("files", "-a"), hidden=not PLUGIN_DEV_ENABLED)
    async def dev_list_plugins(self, ctx: Context) -> None:
        """
        Get a list of all plugin files, including their loaded status.

        Red indicates that the plugin file is unloaded.
        Green indicates that the plugin file is currently loaded.
        """
        await self.list_extensions.callback(self, ctx)

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
