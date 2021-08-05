import logging

from discord.ext import commands
from discord.ext.commands import Context

from modmail.bot import ModmailBot
from modmail.log import ModmailLogger

log: ModmailLogger = logging.getLogger(__name__)


class Meta(commands.Cog):
    """Meta commands to get info about the bot itself."""

    def __init__(self, bot: ModmailBot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx: Context) -> None:
        """Check response time."""
        await ctx.send(f"{round(self.bot.latency * 1000)}ms")

    @commands.command(name="uptime")
    async def uptime(self, ctx: commands.Context) -> None:
        """Get the current uptime of the bot."""
        timestamp = self.bot.start_time.format("X").split(".")[0]
        await ctx.send(f"Start time: <t:{timestamp}:R>")


def setup(bot: ModmailBot) -> None:
    """Load the Meta cog."""
    bot.add_cog(Meta(bot))
