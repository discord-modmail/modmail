import logging
from typing import TYPE_CHECKING, Optional, Union

import arrow
import discord
from arrow import Arrow
from discord.ext import commands
from discord.ext.commands import Context
from discord.utils import escape_markdown

from modmail.utils.cogs import ExtMetadata, ModmailCog
from modmail.utils.converters import Duration
from modmail.utils.threads import ThreadEmbed, Ticket, is_modmail_thread
from modmail.utils.threads.errors import ThreadAlreadyExistsError, ThreadNotFoundError
from modmail.utils.users import check_can_dm_user

if TYPE_CHECKING:
    from modmail.bot import ModmailBot
    from modmail.log import ModmailLogger


EXT_METADATA = ExtMetadata()


BASE_JUMP_URL = "https://discord.com/channels/"
USER_NOT_ABLE_TO_BE_DMED_MESSAGE = (
    "**{0}** is not able to be dmed! This is because they have either blocked the bot, "
    "or they are only accepting direct messages from friends.\n"
    "It is also possible that they are not in the same server as the bot. "
)

logger: "ModmailLogger" = logging.getLogger(__name__)


class TicketsCog(ModmailCog, name="Threads"):
    """A cog for relaying direct messages."""

    def __init__(self, bot: "ModmailBot"):
        self.bot = bot
        # user id, Ticket
        self.relay_channel: Union[
            discord.TextChannel, discord.PartialMessageable
        ] = self.bot.get_partial_messageable(self.bot.config.thread.relay_channel_id)
        self.embed_creator = ThreadEmbed()

    async def init_relay_channel(self) -> None:
        """Fetch the relay channel."""
        self.relay_channel = await self.bot.fetch_channel(self.bot.config.thread.relay_channel_id)

    def get_ticket(self, id: int, /) -> Ticket:
        """Fetch a ticket from the tickets dict."""
        try:
            ticket = self.bot.tickets[id]
        except KeyError:
            raise ThreadNotFoundError(f"Could not find thread from id {id}.")
        else:
            return ticket

    # the reason we're checking for a user here rather than a member is because of future support for
    # a designated server to handle threads and a server where the community resides,
    # so its possible that the user isn't in the server where this command is run.
    @commands.command()
    async def contact(self, ctx: Context, recipient: commands.UserConverter) -> None:
        """
        Open a new ticket with a provided recipient.

        This command uses nothing btw. Not arch.
        """
        if recipient.bot:
            await ctx.send("You can't open a ticket with a bot.")
            return

        try:
            ticket = await self.create_ticket(
                ctx.message, recipient=recipient, check_for_existing_thread=True
            )
        except ThreadAlreadyExistsError:
            thread = self.get_ticket(recipient.id).thread
            await ctx.send(
                f"A thread already exists with {recipient.mention} ({recipient.id})."
                f"You can find it here: <{BASE_JUMP_URL}{thread.guild.id}/{thread.id}>",
                allowed_mentions=discord.AllowedMentions(users=False),
            )
            return

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

        if check_for_existing_thread and recipient.id in self.bot.tickets.keys():
            raise ThreadAlreadyExistsError(recipient.id)

        thread_channel = await self._start_discord_thread(initial_message)
        ticket = Ticket(recipient, thread_channel)

        # add the ticket as both the recipient and the thread ids so they can be retrieved from both sides.
        self.bot.tickets[recipient.id] = ticket
        self.bot.tickets[thread_channel.id] = ticket
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
            embed=self.embed_creator.create_inital_embed_to_guild(message),
            allowed_mentions=allowed_mentions,
        )
        thread_channel = await relayed_msg.create_thread(
            name=str(message.author.name + "-" + message.author.discriminator),
            auto_archive_duration=relayed_msg.channel.default_auto_archive_duration,
        )

        return thread_channel

    async def _relay_message(
        self, ticket: Ticket, message: discord.Message, contents: str = None
    ) -> discord.Message:
        """Send a message to the thread, either from dms or to guild, or from guild to dms."""
        if ticket.recipient.dm_channel is None:
            await ticket.recipient.create_dm()
        if message.guild is not None:
            # thread -> dm
            logger.debug(
                "Relaying message id {0} by {3} from thread {1} to dm channel {2}.".format(
                    message.id, ticket.thread.id, ticket.recipient.dm_channel.id, message.author
                )
            )
            sent_message = await ticket.recipient.send(
                embed=ticket.embed_creator.create_message_embed_to_user(message, contents)
            )
            # also relay it in the thread channel
            new_message = await ticket.thread.send(
                embed=ticket.embed_creator.create_message_embed_to_user(message, contents)
            )
            await message.delete()
            message = new_message
            ticket.last_sent_message = message
        else:
            # dm -> thread
            logger.debug(
                "Relaying message id {0} from dm channel {1} with {3} to thread {2}.".format(
                    message.id, ticket.recipient.dm_channel.id, ticket.thread.id, message.author
                )
            )
            sent_message = await ticket.thread.send(
                embed=ticket.embed_creator.create_message_embed_to_guild(message)
            )

        # add messages to the dict
        ticket.messages[message] = sent_message
        return sent_message

    @is_modmail_thread()
    @commands.command(aliases=("r",))
    async def reply(self, ctx: Context, *, message: str) -> None:
        """Send a reply to the user."""
        ticket = self.get_ticket(ctx.channel.id)
        await self._relay_message(ticket, ctx.message, message)

    @is_modmail_thread()
    @commands.command(aliases=("e",))
    async def edit(self, ctx: Context, message: Optional[discord.Message] = None, *, content: str) -> None:
        """Edit a message in the thread."""
        ticket = self.get_ticket(ctx.channel.id)
        if message is None:
            message = ticket.last_sent_message
        await ticket.messages[message].edit(
            embed=ticket.embed_creator.create_message_embed_to_user(message, content)
        )
        await ctx.message.add_reaction("✅")

    @is_modmail_thread()
    @commands.group(invoke_without_command=True)
    async def close(self, ctx: Context, *, _: Duration = None) -> None:
        """Close the current thread after `after` time from now."""
        # TODO: Implement after duration
        thread_close_embed = discord.Embed(
            title="Thread Closed",
            description=f"{ctx.author.mention} has closed this Modmail thread.",
            timestamp=arrow.utcnow(),
        )

        # clean up variables
        await ctx.send(embed=thread_close_embed)
        ticket = self.bot.tickets[ctx.channel.id]
        try:
            del self.bot.tickets[ticket.thread.id]
            del self.bot.tickets[ticket.recipient.id]
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
            ticket = self.bot.tickets[author.id]
        except KeyError:
            # Thread doesn't exist, so create one.
            ticket = await self.create_ticket(message, check_for_existing_thread=False)
        await self._relay_message(ticket, message)

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
                ticket = self.bot.tickets[channel.id]
            except KeyError:
                # Thread doesn't exist, so there's nowhere to relay the typing event.
                return
            await ticket.recipient.trigger_typing()

        # ! Due to a library bug this tree will never be run
        # it can be tracked here: https://github.com/Rapptz/discord.py/issues/7432
        elif isinstance(channel, discord.DMChannel):
            try:
                ticket = self.bot.tickets[user.id]
            except KeyError:
                # User doesn't have a ticket, so no where to relay the event.
                return
            else:
                await ticket.thread.trigger_typing()

        else:
            return


def setup(bot: "ModmailBot") -> None:
    """Adds the Tickets cog to the bot."""
    bot.add_cog(TicketsCog(bot))
