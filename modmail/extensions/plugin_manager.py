from __future__ import annotations

import asyncio
import logging
import os
import zipfile
from typing import TYPE_CHECKING

from discord.ext import commands
from discord.ext.commands import Context

from modmail.extensions.extension_manager import Action, ExtensionConverter, ExtensionManager
from modmail.utils.addons.converters import PluginWithSourceConverter
from modmail.utils.addons.models import Plugin, SourceTypeEnum
from modmail.utils.addons.plugins import BASE_PATH, PLUGINS, walk_plugins
from modmail.utils.cogs import BotModes, ExtMetadata

if TYPE_CHECKING:
    from modmail.bot import ModmailBot
    from modmail.log import ModmailLogger

EXT_METADATA = ExtMetadata(load_if_mode=BotModes.PRODUCTION)
VALID_PLUGIN_DIRECTORIES = ["plugins", "Plugins"]
logger: ModmailLogger = logging.getLogger(__name__)


class PluginPathConverter(ExtensionConverter):
    """
    Fully qualify the name of a plugin and ensure it exists.

    The * value bypasses this when used with the a plugin manger command.
    """  # noqa: W605

    source_list = PLUGINS
    type = "plugin"
    NO_UNLOAD = None


class PluginManager(ExtensionManager, name="Plugin Manager"):
    """Plugin management commands."""

    type = "plugin"

    def __init__(self, bot: ModmailBot) -> None:
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
        """
        Load plugins given their fully qualified or unqualified names.

        If '\*' is given as the name, all unloaded plugins will be loaded.
        """  # noqa: W605
        await self.load_extensions.callback(self, ctx, *plugins)

    @plugins_group.command(name="unload", aliases=("ul",))
    async def unload_plugins(self, ctx: Context, *plugins: PluginPathConverter) -> None:
        """
        Unload currently loaded plugins given their fully qualified or unqualified names.

        If '\*' is given as the name, all loaded plugins will be unloaded.
        """  # noqa: W605
        await self.unload_extensions.callback(self, ctx, *plugins)

    @plugins_group.command(name="reload", aliases=("r", "rl"))
    async def reload_plugins(self, ctx: Context, *plugins: PluginPathConverter) -> None:
        """
        Reload plugins given their fully qualified or unqualified names.

        If an plugin fails to be reloaded, it will be rolled-back to the prior working state.

        If '\*' is given as the name, all currently loaded plugins will be reloaded.
        """  # noqa: W605
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
    async def plugin_convert_test(self, ctx: Context, *, plugin: PluginWithSourceConverter) -> None:
        """Convert a plugin and given its source information."""
        await ctx.send(f"```py\n{plugin.__repr__()}```")

    @plugins_group.command(name="install", aliases=("",))
    async def install_plugins(self, ctx: Context, *, plugin: PluginWithSourceConverter) -> None:
        """Install plugins from provided repo."""
        plugin: Plugin = plugin
        if plugin.source.source_type is SourceTypeEnum.LOCAL:
            # TODO: check the path of a local plugin
            await ctx.send("This plugin is a local plugin, and likely can be loaded with the load command.")
            return
        logger.debug(f"Received command to download plugin {plugin.name} from {plugin.source.zip_url}")
        async with self.bot.http_session.get(f"https://{plugin.source.zip_url}") as resp:
            if resp.status != 200:
                await ctx.send(f"Downloading {plugin.source.zip_url} did not give a 200")
                return
            raw_bytes = await resp.read()
        if plugin.source.source_type is SourceTypeEnum.REPO:
            file_name = f"{plugin.source.githost}/{plugin.source.user}/{plugin.source.repo}"
        elif plugin.source.source_type is SourceTypeEnum.ZIP:
            file_name = plugin.source.path.rstrip(".zip")
        else:
            raise TypeError("Unsupported source detected.")

        zipfile_path = BASE_PATH / ".cache" / f"{file_name}.zip"

        plugin.source.cache_file = zipfile_path

        if not zipfile_path.exists():
            zipfile_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            # overwriting an existing file
            logger.info("Zip file already exists, overwriting it.")

        with zipfile_path.open("wb") as f:
            f.write(raw_bytes)
        await ctx.send(f"Downloaded {zipfile_path}")

        file = zipfile.ZipFile(zipfile_path)
        print(file.namelist())
        file.printdir()
        print(file.infolist())
        print("-" * 50)
        _temp_direct_children = [p for p in zipfile.Path(file).iterdir()]
        if len(_temp_direct_children) == 1:
            # only one folder, so we probably want to recurse into it
            _folder = _temp_direct_children[0]
            if _folder.is_dir():
                # the zip folder needs to have the extra directory removed,
                # and everything moved up a directory.
                temp_archive = BASE_PATH / ".restructure.zip"
                temp_archive = zipfile.ZipFile(temp_archive, mode="w")
                for path in file.infolist():
                    logger.trace(f"File name: {path.filename}")
                    if (new_name := path.filename.split("/", 1)[-1]) == "":
                        continue
                    temp_archive.writestr(new_name, file.read(path))
                    # given that we are writing to disk, we want to ensure
                    # that we yield to anything that needs the event loop
                    await asyncio.sleep(0)
                temp_archive.close()
                os.replace(temp_archive.filename, file.filename)

                # reset the file so we ensure we have the new archive open
                file.close()
                print(zipfile_path)
                print(file.filename)
                file = zipfile.ZipFile(zipfile_path)

        # TODO: REMOVE THIS SECTION
        # extract the archive
        file.extractall(BASE_PATH / ".extraction")

        # determine plugins in the archive
        archive_plugin_directory = None
        for dir in VALID_PLUGIN_DIRECTORIES:
            dir = dir + "/"
            if dir in file.namelist():
                archive_plugin_directory = dir
                break
        if archive_plugin_directory is None:
            await ctx.send("Looks like there isn't a valid plugin here.")
            return

        archive_plugin_directory = zipfile.Path(file, at=archive_plugin_directory)
        print(archive_plugin_directory)
        lil_pluggies = []
        for path in archive_plugin_directory.iterdir():
            logger.debug(f"archive_plugin_directory: {path}")
            if path.is_dir():
                lil_pluggies.append(archive_plugin_directory.name + "/" + path.name + "/")

        logger.debug(f"Plugins detected: {lil_pluggies}")
        all_lil_pluggies = lil_pluggies
        files = file.namelist()
        for pluggy in all_lil_pluggies:
            for f in files:
                if f == pluggy:
                    continue
                if f.startswith(pluggy):
                    all_lil_pluggies.append(f)
                    print(f)

        # extract the drive
        these_plugins_dir = BASE_PATH / file_name
        print(file.namelist())
        file.extractall(these_plugins_dir, all_lil_pluggies)

        # TODO: rewrite this only need to scan the new directory
        self._resync_extensions()
        temp_new_plugins = [x.strip("/").rsplit("/", 1)[1] for x in lil_pluggies]
        new_plugins = []
        for p in temp_new_plugins:
            logger.debug(p)
            try:
                new_plugins.append(await PluginPathConverter().convert(None, p))
            except commands.BadArgument:
                pass

        self.batch_manage(Action.LOAD, *new_plugins)

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
