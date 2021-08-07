from modmail.bot import ModmailBot
from modmail.exts.extensions._base_class import ExtensionManager


class CogsManager(ExtensionManager):
    """Cogs management commands."""

    def __init__(self, bot: ModmailBot) -> None:
        self.bot = bot

        _extension_type = "cog"
        _aliases = ("ext", "exts", "c", "cogs")
        ExtensionManager.__init__(self, bot, _extension_type, _aliases)


def setup(bot: ModmailBot) -> None:
    """Load the Cogs manager cog."""
    bot.add_cog(CogsManager(bot))
