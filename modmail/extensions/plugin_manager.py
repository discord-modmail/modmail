from discord.ext import commands
from discord.ext.commands import Context

from modmail.bot import ModmailBot
from modmail.extensions.extension_manager import ExtensionConverter, ExtensionManager
from modmail.utils.cogs import ModeMetadata
from modmail.utils.plugin_manager import PLUGINS

EXT_METADATA = ModeMetadata(production=True, develop=True, plugin_dev=True)


class PluginConverter(ExtensionConverter):
    """
    Fully qualify the name of a plugin and ensure it exists.

    The * and ** values bypass this when used with the reload command.
    """

    source_list = PLUGINS
    type = "plugin"


class PluginManager(ExtensionManager):
    """Plugin management commands."""

    type = "plugin"

    def __init__(self, bot: ModmailBot) -> None:
        super().__init__(bot)
        self.all_extensions = PLUGINS

    @commands.group("plugins", aliases=("plug", "plugs"), invoke_without_command=True)
    async def plugins_group(self, ctx: Context) -> None:
        """Install, uninstall, disable, update, and enable installed plugins."""
        await ctx.send_help(ctx.command)

    @plugins_group.command(name="load", aliases=("l",))
    async def load_plugin(self, ctx: Context, *plugins: PluginConverter) -> None:
        """
        Load plugins given their fully qualified or unqualified names.

        If '\*' or '\*\*' is given as the name, all unloaded plugins will be loaded.
        """  # noqa: W605
        await self.load_extensions.callback(self, ctx, *plugins)

    @plugins_group.command(name="unload", aliases=("ul",))
    async def unload_plugins(self, ctx: Context, *plugins: PluginConverter) -> None:
        """
        Unload currently loaded plugins given their fully qualified or unqualified names.

        If '\*' or '\*\*' is given as the name, all loaded plugins will be unloaded.
        """  # noqa: W605
        await self.unload_extensions.callback(self, ctx, *plugins)

    @plugins_group.command(name="reload", aliases=("r",))
    async def reload_plugins(self, ctx: Context, *plugins: PluginConverter) -> None:
        """
        Reload extensions given their fully qualified or unqualified names.

        If an extension fails to be reloaded, it will be rolled-back to the prior working state.

        If '*' is given as the name, all currently loaded extensions will be reloaded.
        If '**' is given as the name, all extensions, including unloaded ones, will be reloaded.
        """
        await self.reload_extensions.callback(self, ctx, *plugins)

    @plugins_group.command(name="list", aliases=("all", "ls"))
    async def list_plugins(self, ctx: Context) -> None:
        """
        Get a list of all extensions, including their loaded status.

        Grey indicates that the extension is unloaded.
        Green indicates that the extension is currently loaded.
        """
        await self.list_extensions.callback(self, ctx)

    # TODO: Implement install/enable/disable/etc


# Delete the commands from ExtensionManager that PluginManager has inherited
# before discord.py tries to re-register them
for command in ExtensionManager.__cog_commands__:
    PluginManager.__cog_commands__.remove(command)


def setup(bot: ModmailBot) -> None:
    """Load the Plugins Manager cog."""
    # PluginManager includes the ExtensionManager
    bot.add_cog(PluginManager(bot))
