from modmail import ModmailBot
from modmail.exts.extensions._base_class import ExtensionManager


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
