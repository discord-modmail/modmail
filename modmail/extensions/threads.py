import logging
import typing as t
from dataclasses import dataclass

import discord

from modmail.bot import ModmailBot
from modmail.log import ModmailLogger
from modmail.utils.cogs import ExtMetadata, ModmailCog

EXT_METADATA = ExtMetadata()

logger: ModmailLogger = logging.getLogger(__name__)


@dataclass()
class ThreadModel:
    """A model of threads."""

    pass


class DmRelay(ModmailCog):
    """A cog for relaying direct messages."""

    threads = list()

    def __init__(self, bot: ModmailBot):
        self.bot = bot
        self.relay_channel: t.Optional[discord.abc.GuildChannel] = None

    @ModmailCog.listener(name="on_message")
    async def on_message(self, message: discord.Message) -> None:
        """Relay all dms to a server channel."""
        if message.author.id == self.bot.user.id:
            return

        if message.guild is not None:
            return

        # all messages are from users into dms now

        # don't relay messages that start with the prefix
        if message.content.startswith(self.bot.config.bot.prefix):
            return

        if self.relay_channel is None:
            self.relay_channel = await self.bot.fetch_channel(875225854349803520)

        allowed_mentions = discord.AllowedMentions(
            everyone=False, users=False, roles=True, replied_user=False
        )
        relayed_msg = await self.relay_channel.send(
            content="<@&845823417571737640>",
            embed=self.format_message_embed(message),
            allowed_mentions=allowed_mentions,
        )

        thread_channel = await relayed_msg.create_thread(name=message.author.name)

        await thread_channel.send(
            content=":exclamation::exclamation::exclamation:", embed=self.format_message_embed(message)
        )

    def format_message_embed(self, message: discord.Message, **kwargs) -> discord.Embed:
        """Given information, return a cute embed."""
        return discord.Embed(
            description=message.content, author=message.author, timestamp=message.created_at, **kwargs
        )

    async def _create__discord_thread(self, message: discord.Message, name: str) -> ThreadModel:
        """
        Create a discord thread.

        This creates a discord thread, and a thread model, with the user and etc.
        message must be a message in the relay channel.
        """
        # Create the thread
        thread: discord.Thread = await message.create_thread(name)

        # Create the thread model
        thread_model = ThreadModel(
            id=thread.id,
            parent=thread.parent,
            recipient=message.author,
            started_at=thread.created_at,
        )

        # Add the thread model to the list
        self.threads.append(thread_model)

        return thread_model


def setup(bot: ModmailBot) -> None:
    """Add the DmRelay cog to the bot."""
    bot.add_cog(DmRelay(bot))
