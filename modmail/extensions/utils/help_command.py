from discord.ext import commands

from modmail.bot import ModmailBot
from modmail.utils.cogs import ModmailCog
from modmail.utils.pagination import ButtonPaginator


class ModmailHelpCommand(commands.DefaultHelpCommand):
    """Custom help command implementation."""

    def __init__(self, **kw):
        kw["paginator"] = ButtonPaginator(prefix="", suffix="")
        super().__init__(**kw)

    async def send_pages(self) -> None:
        """Send the paginator."""
        await self.paginator._paginate(self.get_destination())


class HelpCog(ModmailCog):
    """Containment cog for the custom help command."""

    def __init__(self, bot: ModmailBot):
        self.bot = bot

        self._og_help_command = bot.help_command

        help_command = ModmailHelpCommand()
        help_command.cog = self
        bot.help_command = help_command

    def cog_unload(self) -> None:
        """Reset the help command when the cog is unloaded."""
        self.bot.help_command = self._og_help_command
        super().cog_unload()


def setup(bot: ModmailBot) -> None:
    """Add the help command to the bot."""
    bot.add_cog(HelpCog(bot))
