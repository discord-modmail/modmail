import datetime
import logging
import typing as t

import discord
from discord.ext import commands
from discord.ext.commands import Context

from modmail.bot import ModmailBot
from modmail.config import CONFIG
from modmail.log import ModmailLogger
from modmail.utils.cogs import ExtMetadata, ModmailCog
from modmail.utils.converters import Duration
from modmail.utils.threads import is_thread_channel

EXT_METADATA = ExtMetadata()

logger: ModmailLogger = logging.getLogger(__name__)


class Ticket:
    """
    Represents a ticket.

    This class represents a ticket for Modmail.  A ticket is a way to send
    messages to a specific user.
    """

    user: discord.User
    thread: discord.Thread
    log_message: discord.Message
    close_after: t.Optional[int] = None


class Tickets(ModmailCog, name="Threads"):
    """A cog for relaying direct messages."""

    def __init__(self, bot: ModmailBot):
        self.bot = bot
        self.config = CONFIG

        self.relay_channel: t.Optional[discord.TextChannel] = None

    @staticmethod
    def format_message_embed(message: discord.Message, **kwargs) -> discord.Embed:
        """Given information, return a cute embed."""
        return discord.Embed(
            title=f"{message.author.name}#{message.author.discriminator}({message.author.id})",
            description=str(f"{message.content}"),
            author=message.author,
            timestamp=datetime.datetime.now(),
            **kwargs,
        )

    async def start_discord_thread(self, message: discord.Message) -> discord.Thread:
        """Create a discord thread."""
        allowed_mentions = discord.AllowedMentions(
            everyone=False, users=False, roles=True, replied_user=False
        )
        relayed_msg = await self.relay_channel.send(
            content=f"<@&{self.config.thread.thread_mention_role_id}>",
            embed=self.format_message_embed(message),
            allowed_mentions=allowed_mentions,
        )
        thread_channel = await relayed_msg.create_thread(
            name=str(message.author.id),
            auto_archive_duration=relayed_msg.channel.default_auto_archive_duration,
        )

        return thread_channel

    @ModmailCog.listener(name="on_message")
    async def on_message(self, message: discord.Message) -> None:
        """Relay all dms to a server channel."""
        author = message.author

        if author.id == self.bot.user.id or message.guild:
            return

        # don't relay messages that start with the prefix
        if message.content.startswith(self.bot.config.bot.prefix):
            return

        if not self.relay_channel:
            self.relay_channel = await self.bot.fetch_channel(875225854349803520)

        guild = self.bot.get_guild(self.config.bot.guild_id)
        if thread_channel := discord.utils.get(guild.threads, name=str(author.id)):
            if thread_channel.archived:
                thread_channel = await self.start_discord_thread(message)
        else:
            thread_channel = await self.start_discord_thread(message)

        await thread_channel.send(message.content)

    @is_thread_channel()
    @commands.command(aliases=("r",))
    async def reply(self, ctx: Context, *, message: str) -> None:
        """Send a reply to the user."""
        user = await self.bot.fetch_user(ctx.message.channel.name)
        await user.send(message)
        await ctx.message.add_reaction("📬")

    @is_thread_channel()
    @commands.group(invoke_without_command=True)
    async def close(self, ctx: Context, *, _: Duration = None) -> None:
        """Close the current thread after `after` time from now."""
        # TODO: Implement after duration
        thread_close_embed = discord.Embed(
            title="Thread Closed",
            description=f"{ctx.author.mention} has closed this Modmail thread.",
            timestamp=datetime.datetime.now(),
        )
        await ctx.send(embed=thread_close_embed)
        await ctx.channel.edit(archived=True, locked=False)


def setup(bot: ModmailBot) -> None:
    """Add the Tickets cog to the bot."""
    bot.add_cog(Tickets(bot))
