from discord.ext import commands
from discord.ext.commands import Context

from modmail.bot import ModmailBot
from modmail.extensions.extension_manager import ExtensionConverter, ExtensionManager
from modmail.utils.cogs import BotModes, ExtMetadata
from modmail.utils.plugins import PLUGINS, walk_plugins

EXT_METADATA = ExtMetadata(load_if_mode=BotModes.PRODUCTION)


class PluginConverter(ExtensionConverter):
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
    async def load_plugin(self, ctx: Context, *plugins: PluginConverter) -> None:
        r"""
        Load plugins given their fully qualified or unqualified names.

        If '\*' is given as the name, all unloaded plugins will be loaded.
        """
        await self.load_extensions.callback(self, ctx, *plugins)

    @plugins_group.command(name="unload", aliases=("ul",))
    async def unload_plugins(self, ctx: Context, *plugins: PluginConverter) -> None:
        r"""
        Unload currently loaded plugins given their fully qualified or unqualified names.

        If '\*' is given as the name, all loaded plugins will be unloaded.
        """
        await self.unload_extensions.callback(self, ctx, *plugins)

    @plugins_group.command(name="reload", aliases=("r", "rl"))
    async def reload_plugins(self, ctx: Context, *plugins: PluginConverter) -> None:
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
