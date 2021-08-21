import datetime
import logging
from enum import IntEnum, auto
from typing import TYPE_CHECKING, Dict, Optional, Union

import discord
from arrow import Arrow
from discord.ext import commands
from discord.ext.commands import Context
from discord.utils import escape_markdown

from modmail.utils.cogs import ExtMetadata, ModmailCog
from modmail.utils.converters import Duration
from modmail.utils.threads import ThreadAlreadyExistsError, is_modmail_thread
from modmail.utils.users import check_can_dm_user

if TYPE_CHECKING:
    from modmail.bot import ModmailBot
    from modmail.log import ModmailLogger


EXT_METADATA = ExtMetadata()

logger: "ModmailLogger" = logging.getLogger(__name__)
USER_NOT_ABLE_TO_BE_DMED_MESSAGE = (
    "**{0}** is not able to be dmed! This is because they have either blocked the bot, "
    "or they are only accepting direct messages from friends.\n"
    "It is also possible that they are not in the same server as the bot. "
)


class Target(IntEnum):
    """Targets for thread messages."""

    USER = auto()
    MODMAIL = auto()


class MessageDict(dict):
    """A dict that stores every item as a key and as a value."""

    def __setitem__(self, key: discord.Message, value: discord.Message):
        dict.__setitem__(self, key, value)
        dict.__setitem__(self, value, key)


class Ticket:
    """
    Represents a ticket.

    This class represents a ticket for Modmail.  A ticket is a way to send
    messages to a specific user.
    """

    recipient: discord.User
    thread: discord.Thread
    messages: MessageDict
    log_message: discord.Message
    close_after: Optional[int] = None

    def __init__(self, recipient: discord.User, thread: discord.Thread):
        """
        Creates a Ticket instance.

        At least thread and user are required.
        log_message and close_after are automatically gathered from the thread object
        """
        self.thread = thread
        self.recipient = recipient
        self.log_message: Union[
            discord.Message, discord.PartialMessage
        ] = self.thread.parent.get_partial_message(self.thread.id)
        self.messages = MessageDict()
        self.close_after = self.thread.auto_archive_duration
        logger.trace(f"Created a Ticket object for recipient {recipient} with thread {thread}.")

    async def fetch_log_message(self) -> discord.Message:
        """
        Fetch the log message from the discord api.

        This ensures that log_message is not a PartialMessage, but a full discord.Message.
        """
        self.log_message = await self.thread.parent.fetch_message(self.thread.id)
        return self.log_message


class TicketsCog(ModmailCog, name="Threads"):
    """A cog for relaying direct messages."""

    def __init__(self, bot: "ModmailBot"):
        self.bot = bot
        # user id, Ticket
        self.tickets: Dict[int, Ticket] = dict()
        self.relay_channel: Union[
            discord.TextChannel, discord.PartialMessageable
        ] = self.bot.get_partial_messageable(self.bot.config.thread.relay_channel_id)

    def _format_generic_embed_to_guild() -> discord.Embed:
        """
        Create a generic discord embed object to be sent to the guild.

        This contains configuration and special types which should be in nearly all embed creation methods.
        """
        raise NotImplementedError

    def _format_generic_embed_to_user() -> discord.Embed:
        """
        Create a generic discord embed object to be sent to the user.

        This contains configuration and special types which should be in nearly all embed creation methods.
        """
        raise NotImplementedError

    def _format_inital_embed_to_user(self, message: discord.Message, **kwargs) -> discord.Embed:
        """Create a discord embed object to be sent to the user in reply to their inital dm."""
        raise NotImplementedError

    def _format_inital_embed_to_guild(self, message: discord.Message, **kwargs) -> discord.Embed:
        """
        Create a discord embed object to be sent to the guild on inital dm.

        This is used in the relay_channel, in order to share that there is a new ticket.
        """
        raise NotImplementedError

    def _format_close_embed_to_user(self, message: discord.Message, **kwargs) -> discord.Embed:
        """Create a discord embed object to be sent to the user on thread close."""
        raise NotImplementedError

    def _format_close_embed_to_guild(self, message: discord.Message, **kwargs) -> discord.Embed:
        """Create a discord embed object to be sent to the guild on thread close."""
        raise NotImplementedError

    def _format_message_embed_to_user(
        self,
        message: discord.Message,
        contents: str,
        **kwargs,
    ) -> discord.Embed:
        """Given information, return an embed to be sent to the user."""
        return discord.Embed(
            description=contents,
            timestamp=message.created_at,
            color=message.author.color,
            author=message.author,
            **kwargs,
        )

    def _format_message_embed_to_guild(self, message: discord.Message, **kwargs) -> discord.Embed:
        """Given information, return an embed object to be sent to the server."""
        return discord.Embed(
            title=f"{message.author.name}#{message.author.discriminator}({message.author.id})",
            description=str(f"{message.content}"),
            author=message.author,
            timestamp=message.created_at,
            footer_text=f"Message ID: {message.id}",
            **kwargs,
        )

    def _format_edited_message_embed_to_user(self, message: discord.Message, **kwargs) -> discord.Embed:
        """Creates a new embed from an edited message by staff, to be sent to the end user."""
        raise NotImplementedError

    def _format_edited_message_embed_to_guild(self, message: discord.Message, **kwargs) -> discord.Embed:
        """Creates a new embed to be sent in guild from an edited message."""
        raise NotImplementedError

    async def init_relay_channel(self) -> None:
        """Fetch the relay channel."""
        self.relay_channel = await self.bot.fetch_channel(self.bot.config.thread.relay_channel_id)

    # the reason we're checking for a user here rather than a member is because of future support for
    # a designated server to handle threads and a server where the community resides,
    # so its possible that the user isn't in the server where this command is run.
    @commands.command()
    async def contact(self, ctx: Context, recipient: commands.UserConverter) -> discord.Message:
        """
        Open a new ticket with a provided recipient.

        This command uses nothing btw. Not arch.
        """
        if recipient.bot:
            return await ctx.send("You can't open a ticket with a bot.")

        ticket = await self.create_ticket(ctx.message, recipient=recipient, check_for_existing_thread=True)

        if not await check_can_dm_user(recipient):
            await ticket.thread.send(
                USER_NOT_ABLE_TO_BE_DMED_MESSAGE.format(
                    escape_markdown(f"{recipient.name}#{recipient.discriminator}")
                )
            )

    async def create_ticket(
        self,
        initial_message: discord.Message,
        /,
        *,
        recipient: discord.User = None,
        check_for_existing_thread: bool = True,
        send_initial_message: bool = True,
    ) -> Ticket:
        """
        Creates a bot ticket with a user. Also adds it to the tickets dict.

        At least one of recipient and initial_message must be required.
        If recipient is not provided, it will be determined from the initial_message.

        Parameters
        ----------
        recipient: discord.User

        initial_message: discord.Message

        check_for_existing_thread: bool = True
            Whether to check if there is an existing ticket for the user.
            If there is an existing thread, this method will raise a ThreadAlreadyExistsError exception.

        send_initial_message: bool = True
            Whether to relay the provided initial_message to the user.

        """
        if initial_message is None:
            raise ValueError("initial_message must be provided.")
        if recipient is None:
            recipient = initial_message.author

        if check_for_existing_thread and recipient.id in self.tickets.keys():
            raise ThreadAlreadyExistsError(recipient.id)

        thread_channel = await self._start_discord_thread(initial_message)
        ticket = Ticket(recipient, thread_channel)

        # add the ticket as both the recipient and the thread ids so they can be retrieved from both sides.
        self.tickets[recipient.id] = ticket
        self.tickets[thread_channel.id] = ticket
        return ticket

    async def _start_discord_thread(self, message: discord.Message) -> discord.Thread:
        """Create a discord thread."""
        await self.init_relay_channel()
        allowed_mentions = discord.AllowedMentions(
            everyone=False, users=False, roles=True, replied_user=False
        )
        if self.bot.config.thread.thread_mention_role_id is not None:
            mention = f"<@&{self.bot.config.thread.thread_mention_role_id}>"
        else:
            mention = "@here"
        relayed_msg = await self.relay_channel.send(
            content=mention,
            embed=self._format_thread_embed(message),
            allowed_mentions=allowed_mentions,
        )
        thread_channel = await relayed_msg.create_thread(
            name=str(message.author.name + "-" + message.author.discriminator),
            auto_archive_duration=relayed_msg.channel.default_auto_archive_duration,
        )

        return thread_channel

    async def _send_thread(
        self, ticket: Ticket, message: discord.Message, contents: str = None
    ) -> discord.Message:
        """Send a message to the thread."""
        if ticket.recipient.dm_channel is None:
            await ticket.recipient.create_dm()
        if message.guild is not None:
            # thread -> dm
            logger.debug(
                "Relaying message id {0} by {3} from thread {1} to dm channel {2}.".format(
                    message.id, ticket.thread.id, ticket.recipient.dm_channel.id, message.author
                )
            )
            sent_message = await ticket.recipient.send(embed=self._format_user_embed(message, contents))
        else:
            # dm -> thread
            logger.debug(
                "Relaying message id {0} from dm channel {1} with {3} to thread {2}.".format(
                    message.id, ticket.recipient.dm_channel.id, ticket.thread.id, message.author
                )
            )
            sent_message = await ticket.thread.send(embed=self._format_thread_embed(message))
        # add messages to the dict
        ticket.messages[message] = sent_message

    # listen for all messages
    @is_modmail_thread()
    @commands.command(aliases=("r",))
    async def reply(self, ctx: Context, *, message: str) -> None:
        """Send a reply to the user."""
        await self._send_thread(self.tickets[ctx.channel.id], ctx.message, message)
        await ctx.message.add_reaction("📬")

    @is_modmail_thread()
    @commands.group(invoke_without_command=True)
    async def close(self, ctx: Context, *, _: Duration = None) -> None:
        """Close the current thread after `after` time from now."""
        # TODO: Implement after duration
        thread_close_embed = discord.Embed(
            title="Thread Closed",
            description=f"{ctx.author.mention} has closed this Modmail thread.",
            timestamp=datetime.datetime.now(),
        )

        # clean up variables
        await ctx.send(embed=thread_close_embed)
        ticket = self.tickets[ctx.channel.id]
        try:
            del self.tickets[ticket.thread.id]
            del self.tickets[ticket.recipient.id]
        except KeyError:
            logger.warning("Ticket not found in tickets dict when attempting removal.")
        # ensure we get rid of the ticket messages, as this can be an extremely large dict
        del ticket.messages
        del ticket
        await ctx.channel.edit(archived=True, locked=False)
        logger.debug(f"{ctx.author} has closed thread {ctx.channel.id}.")

    @ModmailCog.listener(name="on_message")
    async def on_message(self, message: discord.Message) -> None:
        """Relay all dms to a thread channel."""
        author = message.author

        if author.id == self.bot.user.id:
            return

        if message.guild:
            return

        try:
            ticket = self.tickets[author.id]
        except KeyError:
            # Thread doesn't exist, so create one.
            ticket = await self.create_ticket(message, check_for_existing_thread=False)
        await self._send_thread(ticket, message)

    @ModmailCog.listener(name="on_typing")
    async def on_typing(
        self,
        channel: discord.abc.Messageable,
        user: Union[discord.User, discord.Member],
        _: Arrow,
    ) -> None:
        """Relay typing events to the thread channel."""
        logger.trace(f"Received typing event for {user} in channel {channel}.")
        if user.id == self.bot.user.id:
            return

        # only work in dms or a thread channel

        if isinstance(channel, discord.Thread):
            try:
                ticket = self.tickets[channel.id]
            except KeyError:
                # Thread doesn't exist, so there's nowhere to relay the typing event.
                return
            await ticket.recipient.trigger_typing()

        # ! Due to a library bug this tree will never be run
        # it can be tracked here: https://github.com/Rapptz/discord.py/issues/7432
        elif isinstance(channel, discord.DMChannel):
            try:
                ticket = self.tickets[user.id]
            except KeyError:
                # User doesn't have a ticket, so no where to relay the event.
                return
            else:
                await ticket.thread.trigger_typing()

        else:
            return


def setup(bot: "ModmailBot") -> None:
    """Add the Tickets cog to the bot."""
    bot.add_cog(TicketsCog(bot))
