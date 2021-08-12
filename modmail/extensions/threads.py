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
from modmail.utils.decorators import is_thread_channel
from modmail.utils.messages import sub_clyde

EXT_METADATA = ExtMetadata()

logger: ModmailLogger = logging.getLogger(__name__)


class DmRelay(ModmailCog):
    """A cog for relaying direct messages."""

    def __init__(self, bot: ModmailBot):
        self.bot = bot
        self.config = CONFIG

        self.relay_channel: t.Optional[discord.abc.GuildChannel] = None
        self.webhook_id: int = self.config.thread.thread_relay_webhook_id
        self.webhook: t.Optional[discord.Webhook] = None

        self.bot.loop.create_task(self.fetch_webhook())

    async def fetch_webhook(self) -> None:
        """Fetches the webhook object, so we can post to it."""
        await self.bot.wait_until_guild_available()

        try:
            self.webhook = await self.bot.fetch_webhook(self.webhook_id)
        except discord.HTTPException:
            logger.exception(f"Failed to fetch webhook with id `{self.webhook_id}`")

    async def send_webhook_message(self, message: discord.Message, thread: discord.Thread) -> discord.Message:
        """
        Send a message using the provided webhook.

        This uses sub_clyde() and tries for an HTTPException to ensure it doesn't crash.
        """
        try:
            return await self.webhook.send(
                content=message.content,
                username=sub_clyde(message.author.name),
                avatar_url=message.author.avatar,
                thread=thread.id,
            )
        except discord.HTTPException:
            logger.exception("Failed to send a message to the webhook!")

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
        thread_channel = await relayed_msg.start_thread(name=str(message.author.id), auto_archive_duration=5)

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

        await self.send_webhook_message(message, thread_channel)

    @is_thread_channel()
    @commands.group(invoke_without_command=True)
    async def close(self, ctx: Context, *, _: Duration = None) -> None:
        """Close the current thread after `after` time from now."""
        # TODO: Implement after duration
        await ctx.channel.edit(archived=True, locked=True)
        thread_close_embed = discord.Embed(
            title="Thread Closed",
            description=f"{ctx.author.mention} has closed this Modmail thread.",
            timestamp=datetime.datetime.now(),
        )
        await ctx.send(embed=thread_close_embed)


def setup(bot: ModmailBot) -> None:
    """Add the DmRelay cog to the bot."""
    bot.add_cog(DmRelay(bot))
