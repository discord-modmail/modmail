import asyncio
import datetime
import logging
from typing import TYPE_CHECKING, Optional, Union

import discord
from arrow import Arrow
from discord import Embed
from discord.ext import commands, tasks
from discord.ext.commands import Context
from discord.utils import escape_markdown

from modmail.utils.cogs import ExtMetadata, ModmailCog
from modmail.utils.converters import Duration
from modmail.utils.threads import Ticket, is_modmail_thread
from modmail.utils.threads.errors import ThreadAlreadyExistsError, ThreadNotFoundError
from modmail.utils.users import check_can_dm_user


if TYPE_CHECKING:
    from modmail.bot import ModmailBot
    from modmail.log import ModmailLogger

EXT_METADATA = ExtMetadata()


BASE_JUMP_URL = "https://discord.com/channels"
USER_NOT_ABLE_TO_BE_DMED_MESSAGE = (
    "**{0}** is not able to be dmed! This is because they have either blocked the bot, "
    "or they are only accepting direct messages from friends.\n"
    "It is also possible that they are not in the same server as the bot. "
)
ON_SUCCESS_EMOJI = "\u2705"  # ✅

# This will be part of configuration later, so its stored in globals for now
ENABLE_DM_TO_GUILD_TYPING = False  # Library bug prevents this form working right now
ENABLE_GUILD_TO_DM_TYPING = False

USE_AUDIT_LOGS = True
logger: "ModmailLogger" = logging.getLogger(__name__)


class TicketsCog(ModmailCog, name="Threads"):
    """A cog for relaying direct messages."""

    def __init__(self, bot: "ModmailBot"):
        self.bot = bot
        # user id, Ticket
        self.relay_channel: Union[
            discord.TextChannel, discord.PartialMessageable
        ] = self.bot.get_partial_messageable(self.bot.config.thread.relay_channel_id)
        self.thread_create_delete_lock = asyncio.Lock()

        self.use_audit_logs: bool = USE_AUDIT_LOGS
        self.fetch_necessary_values.start()

    async def init_relay_channel(self) -> None:
        """Fetch the relay channel."""
        self.relay_channel = await self.bot.fetch_channel(self.bot.config.thread.relay_channel_id)

    @tasks.loop(count=1)
    async def fetch_necessary_values(self) -> None:
        """Fetch the audit log permission."""
        self.relay_channel: discord.TextChannel = await self.bot.fetch_channel(self.relay_channel.id)
        self.relay_channel.guild = await self.bot.fetch_guild(self.relay_channel.guild.id)
        me = await self.relay_channel.guild.fetch_member(self.bot.user.id)
        self.use_audit_logs = USE_AUDIT_LOGS & me.guild_permissions.view_audit_log
        logger.debug("Fetched relay channel and use_audit_log perms")

    def cog_unload(self) -> None:
        """Cancel any tasks that may be running on unload."""
        self.fetch_necessary_values.cancel()

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
    async def contact(self, ctx: Context, recipient: Union[discord.User, discord.Member]) -> None:
        """
        Open a new ticket with a provided recipient.

        This will create a new ticket with the recipient, if a ticket does not already exist.
            If a ticket already exists, a message will be sent in reply with a link to the existing ticket.
        If the user is not able to be dmed, a message will be sent to the channel.
        """
        if recipient.bot:
            if recipient == self.bot.user:
                await ctx.send("I'm perfect, you can't open a ticket with me.")
                return
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
                f"You can find it here: <{BASE_JUMP_URL}/{thread.guild.id}/{thread.id}>",
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

        # lock this next session, since we're checking if a thread already exists here
        # we want to ensure that anything entering this section can get validated.
        async with self.thread_create_delete_lock:
            if check_for_existing_thread and recipient.id in self.bot.tickets.keys():
                raise ThreadAlreadyExistsError(recipient.id)

            thread_channel = await self._start_discord_thread(initial_message, recipient)
            ticket = Ticket(recipient, thread_channel)

            # add the ticket as both the recipient and the thread ids so
            # the tickets can be retrieved from both users or threads.
            self.bot.tickets[recipient.id] = ticket
            self.bot.tickets[thread_channel.id] = ticket

        return ticket

    async def _start_discord_thread(
        self, message: discord.Message, recipient: discord.User = None
    ) -> discord.Thread:
        """Create a discord thread."""
        await self.init_relay_channel()
        if recipient is None:
            recipient = message.author
        allowed_mentions = discord.AllowedMentions(
            everyone=False, users=False, roles=True, replied_user=False
        )
        if self.bot.config.thread.thread_mention_role_id is not None:
            mention = f"<@&{self.bot.config.thread.thread_mention_role_id}>"
        else:
            mention = "@here"
        embed = Embed(author=message.author, description=message.content)
        relayed_msg = await self.relay_channel.send(
            content=mention,
            embed=embed,
            allowed_mentions=allowed_mentions,
        )
        thread_channel = await relayed_msg.create_thread(
            name=str(recipient.name + "-" + recipient.discriminator),
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
            embed = Embed(
                description=contents,
                timestamp=message.created_at,
                color=message.author.color,
                author=message.author,
            )
            # make a reply if it was a reply
            dm_reference_message = None
            guild_reference_message = None
            if message.reference is not None:
                # don't want to fail a reference
                message.reference.fail_if_not_exists = False
                guild_reference_message = message.reference
                try:
                    dm_reference_message = ticket.messages[message.reference.message_id].to_reference(
                        fail_if_not_exists=False
                    )
                except KeyError:
                    pass

            sent_message = await ticket.recipient.send(embed=embed, reference=dm_reference_message)

            # also relay it in the thread channel
            embed.set_footer(text=f"User ID: {message.author.id}")
            new_message = await ticket.thread.send(embed=embed, reference=guild_reference_message)
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
            # make a reply if it was a reply
            guild_reference_message = None
            if message.reference is not None:
                # don't want to fail a reference
                message.reference.fail_if_not_exists = False
                try:
                    guild_reference_message = ticket.messages[message.reference.message_id].to_reference(
                        fail_if_not_exists=False
                    )
                except KeyError:
                    pass

            sent_message = await ticket.thread.send(
                embed=Embed(
                    description=str(f"{message.content}"),
                    author=message.author,
                    timestamp=message.created_at,
                    footer_text=f"Message ID: {message.id}",
                ),
                reference=guild_reference_message,
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

        # edit user message
        user_message = ticket.messages[message]
        embed = user_message.embeds[0]
        embed.description = content
        await user_message.edit(embed=embed)
        del embed

        # edit guild message
        embed = message.embeds[0]
        embed.description = content
        await message.edit(embed=embed)
        del embed

        await ctx.message.add_reaction(ON_SUCCESS_EMOJI)

    @is_modmail_thread()
    @commands.command(aliases=("d", "del"))
    async def delete(self, ctx: Context, message: Optional[discord.Message] = None) -> None:
        """Delete a message in the thread."""
        ticket = self.get_ticket(ctx.channel.id)
        if message is None:
            message = ticket.last_sent_message
            ticket.last_sent_message = None
        await ticket.messages[message].delete()
        await message.delete()
        await ctx.message.add_reaction(ON_SUCCESS_EMOJI)

    async def _close_thread(
        self,
        ticket: Ticket,
        closer: Optional[Union[discord.User, discord.Member]] = None,
        time: Optional[datetime.datetime] = None,
        discord_thread_already_archived: bool = False,
        notify_user: bool = True,
        automatically_archived: bool = False,
    ) -> None:
        """
        Close the current thread after `after` time from now.

        Note: This method destroys the Ticket object.
        """
        if closer is not None:
            thread_close_embed = discord.Embed(
                title="Thread Closed",
                description=f"{closer.mention} has closed this Modmail thread.",
                timestamp=Arrow.utcnow().datetime,
            )
        else:
            thread_close_embed = discord.Embed(
                title="Thread Closed",
                description="This thread has been closed.",
                timestamp=Arrow.utcnow().datetime,
            )

        async with self.thread_create_delete_lock:
            # clean up variables
            if not discord_thread_already_archived:
                await ticket.thread.send(embed=thread_close_embed)
            if notify_user:
                # user may have dms closed
                try:
                    await ticket.recipient.send(embed=thread_close_embed)
                except discord.HTTPException:
                    logger.debug(f"{ticket.recipient} is unable to be dmed. Skipping.")
                    pass

            try:
                del self.bot.tickets[ticket.thread.id]
                del self.bot.tickets[ticket.recipient.id]
            except KeyError:
                logger.warning("Ticket not found in tickets dict when attempting removal.")
            # ensure we get rid of the ticket messages, as this can be an extremely large dict
            del ticket.messages

        await ticket.thread.edit(archived=True, locked=False)

        if closer is not None:
            logger.debug(f"{closer!s} has closed thread {ticket.thread!s}.")
        else:
            logger.debug(f"{ticket.thread!s} has been closed. A user was not provided.")

    @is_modmail_thread()
    @commands.group(invoke_without_command=True)
    async def close(self, ctx: Context, *, _: Duration = None) -> None:
        """Close the current thread after `after` time from now."""
        # TODO: Implement after duration
        try:
            ticket = self.bot.tickets[ctx.channel.id]
        except KeyError:
            await ctx.send("Error: this thread is not in the list of tickets.")
            return

        await self._close_thread(ticket, ctx.author)

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
            await message.channel.send(
                embed=Embed(
                    title="Ticket Opened",
                    description=f"Thanks for dming {self.bot.user.name}! "
                    "A member of our staff will be with you shortly!",
                    timestamp=message.created_at,
                )
            )
        else:
            await self._relay_message(ticket, message)

        await message.add_reaction(ON_SUCCESS_EMOJI)

    @ModmailCog.listener(name="on_typing")
    async def on_typing(
        self,
        channel: discord.abc.Messageable,
        user: Union[discord.User, discord.Member],
        _: Arrow,
    ) -> None:
        """Relay typing events to the thread channel."""
        if user.id == self.bot.user.id:
            return

        # only work in dms or a thread channel

        if ENABLE_GUILD_TO_DM_TYPING and isinstance(channel, discord.Thread):
            try:
                ticket = self.bot.tickets[channel.id]
            except KeyError:
                # Thread doesn't exist, so there's nowhere to relay the typing event.
                return
            logger.debug(f"Relaying typing event from {user!s} in {channel!s} to {ticket.recipient!s}.")
            await ticket.recipient.trigger_typing()

        # ! Due to a library bug this tree will never be run
        # it can be tracked here: https://github.com/Rapptz/discord.py/issues/7432
        elif ENABLE_DM_TO_GUILD_TYPING and isinstance(channel, discord.DMChannel):
            try:
                ticket = self.bot.tickets[user.id]
            except KeyError:
                # User doesn't have a ticket, so no where to relay the event.
                return
            else:
                logger.debug(f"Relaying typing event from {user!s} in {channel!s} to {ticket.recipient!s}.")

                await ticket.thread.trigger_typing()

        else:
            return

    @ModmailCog.listener("on_thread_update")
    async def on_thread_archive(self, before: discord.Thread, after: discord.Thread) -> None:
        """
        Archives a thread after a preset time of it being automatically archived.

        This trigger only handles thread archiving.
        """
        # we only care about edits that archive the thread
        if before.archived != after.archived and not after.archived:
            return

        # channel must have the parent of the relay channel
        # while this should never change, I'm using before in case for some reason
        # threads get the support to change their parent channel, which would be great.
        if before.parent_id != self.relay_channel.id:
            return

        # ignore the bot closing threads
        # NOTE: archiver_id is always gonna be None.
        # HACK: Grab an item from the audit log to get this user.
        archiver = None
        automatically_archived = False
        if self.use_audit_logs:
            async for event in after.guild.audit_logs(limit=4, action=discord.AuditLogAction.thread_update):
                if (
                    event.target.id == after.id
                    and not getattr(event.before, "archived", None)
                    and getattr(event.after, "archived", None)
                ):
                    archiver = event.user
                    break

            if archiver is None:
                automatically_archived = True
            elif self.bot.user == archiver:
                logger.trace("Received a thread archive event which was caused by me. Skipping actions.")
                return
        else:
            # check the last message id
            now = Arrow.utcnow().datetime
            last_message_time = discord.Object(after.last_message_id).created_at
            print()
            if before.auto_archive_duration <= (now - last_message_time).total_seconds():
                # thread was automatically archived, probably.
                automatically_archived = True

        # checks passed, closing the ticket
        try:
            ticket = self.bot.tickets[after.id]
        except KeyError:
            logger.debug(
                "While closing a ticket, somehow checks passed but the thread did not exist... "
                "This is likely due to missing audit log permissions."
            )
            return

        await self._close_thread(
            ticket,
            archiver,
            automatically_archived=automatically_archived,
        )


def setup(bot: "ModmailBot") -> None:
    """Adds the Tickets cog to the bot."""
    bot.add_cog(TicketsCog(bot))
