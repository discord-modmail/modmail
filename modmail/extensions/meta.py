import logging

from discord.ext import commands

from modmail.bot import ModmailBot
from modmail.log import ModmailLogger
from modmail.utils.cogs import ExtMetadata, ModmailCog


log: ModmailLogger = logging.getLogger(__name__)

EXT_METADATA = ExtMetadata()


class Meta(ModmailCog):
    """Meta commands to get info about the bot itself."""

    def __init__(self, bot: ModmailBot):
        self.bot = bot

    @commands.command(name="ping", aliases=("pong",))
    async def ping(self, ctx: commands.Context) -> None:
        """Ping the bot to see its latency and state."""
        await ctx.send(f"{round(self.bot.latency * 1000)}ms")

    @commands.command(name="uptime")
    async def uptime(self, ctx: commands.Context) -> None:
        """Get the current uptime of the bot."""
        timestamp = round(float(self.bot.start_time.format("X")))
        await ctx.send(f"Start time: <t:{timestamp}:R>")

    @commands.command(name="prefix")
    async def prefix(self, ctx: commands.Context) -> None:
        """Return the configured prefix."""
        await ctx.send(f"My current prefix is `{self.bot.config.bot.prefix}`")


def setup(bot: ModmailBot) -> None:
    """Load the Meta cog."""
    bot.add_cog(Meta(bot))
