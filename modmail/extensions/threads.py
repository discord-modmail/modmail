import asyncio
import contextlib
import copy
import datetime
import inspect
import logging
from typing import TYPE_CHECKING, Dict, Generator, List, NoReturn, Optional, Set, Tuple, Union

import arrow
import discord
from discord import Embed
from discord.ext import commands
from discord.ext.commands import Context
from discord.utils import escape_markdown

from modmail.utils.cogs import ExtMetadata, ModmailCog
from modmail.utils.extensions import BOT_MODE, BotModes
from modmail.utils.threads import Ticket, is_modmail_thread
from modmail.utils.threads.errors import ThreadAlreadyExistsError, ThreadNotFoundError
from modmail.utils.time import TimeStampEnum, get_discord_formatted_timestamp
from modmail.utils.users import check_can_dm_user


if TYPE_CHECKING:  # pragma: nocover
    from modmail.bot import ModmailBot
    from modmail.log import ModmailLogger

EXT_METADATA = ExtMetadata()

DEV_MODE_ENABLED = BOT_MODE & BotModes.DEVELOP

BASE_JUMP_URL = "https://discord.com/channels"
DM_FAILURE_MESSAGE = (
    "**{user!s}** is not able to be DMed! This is because they have either blocked the bot, "
    "or they are only accepting direct messages from friends.\n"
    "It is also possible that they do not share a server with the bot."
)
ON_SUCCESS_EMOJI = "\u2705"  # ✅
ON_FAILURE_EMOJI = "\u274c"  # :x:

# This will be part of configuration later, so its stored in globals for now
FORWARD_USER_TYPING = False  # Library bug prevents this from working right now
FORWARD_MODERATOR_TYPING = False

# NOTE: Since discord removed `threads.archiver_id`, (it will always be `None` now), and the
# only way to get the user who archived the thread is to use the Audit logs.
# however, this permission is not required to have basic functionality.
# this permission
USE_AUDIT_LOGS = True

NO_REPONSE_COLOUR = discord.Colour.red()
HAS_RESPONSE_COLOUR = discord.Colour.yellow()
CLOSED_COLOUR = discord.Colour.green()

FORWARDED_DM_COLOR = discord.Colour.dark_teal()  # messages received from dms
INTERNAL_REPLY_COLOR = discord.Colour.teal()  # messages sent, shown in thread

MAX_CACHED_MESSAGES_PER_THREAD = 10

IMAGE_EXTENSIONS = (".png", ".apng", ".gif", ".webm", "jpg", ".jpeg")

logger: "ModmailLogger" = logging.getLogger(__name__)


class RepliedOrRecentMessageConverter(commands.Converter):
    """
    Custom converter to return discord Message from within modmail threads.

    First attempts with the standard message converter, and upon failure,
    will attempt to get the referenced message.
    If that fails, will pop the ticket's recent messages.
    """

    def __init__(self, optional: bool = False, require_argument_empty: bool = False):
        """
        Set up state.

        Optional
        True - return tuple of message/errors
        False - return tuple of message/None, raise errors

        require_argument_empty
        True - requires passed argument is effectively None
        False - doesn't do above check
        """
        self.optional = optional
        self.require_argument_empty = require_argument_empty

    async def convert(self, ctx: Context, argument: str) -> Tuple[Optional[discord.Message], Optional[str]]:
        """Converting implementation. See class docstring for more information."""
        print(ctx.command.name)

        def or_raise(err: Exception) -> Union[Tuple[None, Exception], NoReturn]:
            if self.optional:
                return None, err
            else:
                raise err

        try:
            return await commands.MessageConverter().convert(ctx, argument), None
        except commands.CommandError:
            pass

        if self.require_argument_empty and len(argument):
            return or_raise(commands.CommandError("Provided argument is not empty."))

        if ctx.message.reference is not None:
            ref = ctx.message.reference
            message = ref.resolved or await ctx.channel.fetch_message(ref.message_id)
        else:
            ticket: Ticket = await ctx.bot.get_cog("Threads").fetch_ticket(ctx.channel.id)
            if ticket is None:
                return or_raise(commands.CommandError("There's no message here to action on!"))
            try:
                message = ticket.last_sent_messages[-1]
            except IndexError:
                return or_raise(commands.CommandError("There's no message here to action on!"))

        # undo eating this parameter
        # this means that the argument passed here will be passed to the next parameter
        # but thankfully we can still get our result from here
        ctx.view.undo()

        if message.author.id != ctx.bot.user.id:
            logger.info("Edit command contained a reply, but was not to one of my messages so skipping.")
            return or_raise(commands.CommandError("The replied message is not a message I can modify."))

        return message, None


class TicketsCog(ModmailCog, name="Threads"):
    """A cog for relaying direct messages."""

    def __init__(self, bot: "ModmailBot"):
        self.bot = bot
        super().__init__(bot)
        # validation for this configuration variable is be defered to fully implementing
        # a new configuration system
        self.relay_channel: Union[
            discord.TextChannel, discord.PartialMessageable
        ] = self.bot.get_partial_messageable(self.bot.config.user.threads.relay_channel_id)

        self.dms_to_users: Dict[int, int] = dict()  # key: dm_channel.id, value: user.id

        # message deletion events are messed up, so we have to use these sets
        # to track if we deleted a message, and if we have already relayed it or not.
        # these lists hold the ids of deleted messages that have
        # been acted on before a on_msg_delete event is received

        self.dm_deleted_messages: Set[int] = set()  # message.id of the bot's deleted messages in dms
        self.thread_deleted_messages: Set[int] = set()  # message.id of the bot's deleted messsages in thread

        self.thread_create_delete_lock = asyncio.Lock()
        self.thread_create_lock = asyncio.Lock()

        self.use_audit_logs: bool = USE_AUDIT_LOGS
        self.bot.loop.create_task(self.fetch_necessary_values())

    async def init_relay_channel(self) -> None:
        """Fetch the relay channel."""
        self.relay_channel = await self.bot.fetch_channel(self.bot.config.user.threads.relay_channel_id)

    async def fetch_necessary_values(self) -> None:
        """Fetch the audit log permission."""
        self.relay_channel: discord.TextChannel = await self.bot.fetch_channel(self.relay_channel.id)
        # a little bit of hackery because for some odd reason, the guild object is not always complete
        self.relay_channel.guild = await self.bot.fetch_guild(self.relay_channel.guild.id)
        me = await self.relay_channel.guild.fetch_member(self.bot.user.id)
        self.use_audit_logs = USE_AUDIT_LOGS and me.guild_permissions.view_audit_log
        logger.debug("Fetched relay channel and use_audit_log perms")

    def cog_unload(self) -> None:
        """Cancel any tasks that may be running on unload."""
        super().cog_unload()

    async def add_ticket(self, ticket: Ticket, /) -> Ticket:
        """Save a newly created ticket."""
        self.bot._tickets[ticket.recipient.id] = ticket
        self.bot._tickets[ticket.thread.id] = ticket
        return ticket

    async def fetch_ticket(self, id: int, /, raise_exception: bool = False) -> Optional[Ticket]:
        """
        Fetch a ticket from the tickets dict.

        In the future this will be hooked into the database.

        By default, returns None if a ticket cannot be found.
        However, if raise_exception is True, then this function will raise a ThreadNotFoundError
        """
        # given that this is an async method, it is expected to yield somewhere
        # this gives way to any waiting coroutines while here, temporarily
        await asyncio.sleep(0)
        try:
            ticket = self.bot._tickets[id]
        except KeyError:
            if raise_exception:
                raise ThreadNotFoundError(f"Could not find thread from id {id}.")
            return None
        else:
            return ticket

    def get_user_from_dm_channel_id(self, id: int, /) -> int:
        """Get a user id from a dm channel id. Raises a KeyError if user is not found."""
        return self.users_to_channels[id]

    # the reason we're checking for a user here rather than a member is because of future support for
    # a designated server to handle threads and a server where the community resides,
    # so it's possible that the user isn't in the server where this command is run.
    @commands.command()
    async def contact(
        self, ctx: Context, recipient: Union[discord.User, discord.Member], *, reason: str = ""
    ) -> None:
        """
        Open a new ticket with a provided recipient.

        This will create a new ticket with the recipient, if a ticket does not already exist.
            If a ticket already exists, a message will be sent in reply with a link to the existing ticket.
        If the user is not able to be DMed, a message will be sent to the channel.
        """
        if recipient.bot:
            if recipient == self.bot.user:
                await ctx.send("I'm perfect, you can't open a ticket with me.")
                return
            await ctx.send("You can't open a ticket with a bot.")
            return

        try:
            async with self.thread_create_lock:
                ticket = await self.create_ticket(
                    ctx.message,
                    recipient=recipient,
                    raise_for_preexisting=True,
                    send_initial_message=False,
                    description=reason,
                    creator=ctx.message.author,
                )
        except ThreadAlreadyExistsError:
            thread = (await self.fetch_ticket(recipient.id)).thread
            await ctx.send(
                f"A thread already exists with {recipient.mention} ({recipient.id})."
                f"You can find it here: <{BASE_JUMP_URL}/{thread.guild.id}/{thread.id}>",
                allowed_mentions=discord.AllowedMentions(users=False),
            )
            return

        if not await check_can_dm_user(recipient):
            await ticket.thread.send(DM_FAILURE_MESSAGE.format(user=escape_markdown(str(recipient))))

    async def create_ticket(
        self,
        initial_message: discord.Message,
        /,
        *,
        recipient: discord.User = None,
        raise_for_preexisting: bool = True,
        send_initial_message: bool = True,
        description: str = None,
        creator: Union[discord.User, discord.Member] = None,
    ) -> Ticket:
        """
        Creates a bot ticket with a user. Also adds it to the tickets dict.

        One of recipient and initial_message must be provided.
        If recipient is not provided, it will be determined from the initial_message.

        Parameters
        ----------
        initial_message: discord.Message

        recipient: discord.User

        raise_for_preexisting: bool = True
            Whether to check if there is an existing ticket for the user.
            If there is an existing thread, this method will raise a ThreadAlreadyExistsError exception.

        send_initial_message: bool = True
            Whether to relay the provided initial_message to the user.

        """
        recipient = recipient or initial_message.author

        # lock this next session, since we're checking if a thread already exists here
        # we want to ensure that anything entering this section can get validated.
        async with self.thread_create_delete_lock:
            if recipient.id in self.bot._tickets.keys():
                if raise_for_preexisting:
                    raise ThreadAlreadyExistsError(recipient.id)
                else:
                    return await self.fetch_ticket(recipient.id)

            thread_channel, thread_msg = await self._start_discord_thread(
                initial_message, recipient, description=description, creator=creator
            )
            ticket = Ticket(
                recipient,
                thread_channel,
                has_sent_initial_message=send_initial_message,
                log_message=thread_msg,
            )
            # add the ticket as both the recipient and the thread ids so
            # the tickets can be retrieved from both users or threads.
            await self.add_ticket(ticket)

            # also save user dm channel id
            if recipient.dm_channel is None:
                await recipient.create_dm()
            self.dms_to_users[recipient.dm_channel.id] = recipient.id

        return ticket

    async def _start_discord_thread(
        self,
        message: discord.Message,
        recipient: discord.User = None,
        *,
        embed: discord.Embed = None,
        description: str = None,
        creator: Union[discord.User, discord.Member] = None,
        **send_kwargs,
    ) -> Tuple[discord.Thread, discord.Message]:
        """
        Create a thread in discord off of a provided message.

        Sends an initial message, and returns the thread and the first message sent in the thread.
        Any kwargs not defined in the method signature are forwarded to the discord.Messageable.send method
        """
        await self.init_relay_channel()

        recipient = recipient or message.author
        if send_kwargs.get("allowed_mentions") is None:
            send_kwargs["allowed_mentions"] = discord.AllowedMentions(
                everyone=False, users=False, roles=True, replied_user=False
            )
        # TODO: !CONFIG add to configuration system.
        if self.bot.config.user.threads.thread_mention_role_id is not None:
            mention = f"<@&{self.bot.config.user.threads.thread_mention_role_id}>"
        else:
            mention = "@here"

        if description is None:
            description = message.content
        description = description.strip()

        if creator:
            description += f"\nOpened by {creator!s}"

        embed = discord.Embed(
            title=f"{discord.utils.escape_markdown(recipient.name,ignore_links=False)}"
            f"#{recipient.discriminator} (`{recipient.id}`)",
            description=f"{description}",
            timestamp=datetime.datetime.now(),
            color=NO_REPONSE_COLOUR,
        )
        embed.add_field(
            name="Opened since",
            value=get_discord_formatted_timestamp(arrow.utcnow(), TimeStampEnum.RELATIVE_TIME),
        )

        relayed_msg = await self.relay_channel.send(content=mention, embed=embed, **send_kwargs)
        try:
            thread_channel = await relayed_msg.create_thread(
                name=f"{recipient!s}".replace("#", "-"),
                auto_archive_duration=relayed_msg.channel.default_auto_archive_duration,
            )
        except discord.HTTPException as e:
            if e.code != 50_035:
                raise
            # repeat the request but using the user id and discrim
            # 50035 means that the user has some banned characters or phrases in their name
            thread_channel = await relayed_msg.create_thread(
                name=recipient.id, auto_archive_duration=relayed_msg.channel.default_auto_archive_duration
            )

        return thread_channel, relayed_msg

    async def resolve_mirror_message_for_manipulation(
        self,
        ctx: Context,
        ticket: Ticket,
        message: discord.Message,
    ) -> Optional[Tuple[discord.Message, discord.Message]]:
        """Find the corresponding dm message and raise any errors if the bot did not send that message."""
        try:
            user_message = ticket.messages[message]
        except KeyError:
            try:
                ticket.last_sent_messages.remove(message)
            except ValueError:
                pass
            await ctx.send(
                "Sorry, this is not a message that I can edit.",
                reference=message.to_reference(fail_if_not_exists=False),
            )

            raise

        if user_message.author.id != self.bot.user.id:
            raise commands.CommandError(
                "DM message author is me. It seems like this was a message that you received."
            )
        return user_message, message

    @contextlib.asynccontextmanager
    async def handle_success(self, ctx: Context) -> Generator[None, None, None]:
        """If any exceptions are thrown, a failure emoji is added and the exception is reraised."""
        try:
            yield
        except Exception:
            await ctx.message.add_reaction(ON_FAILURE_EMOJI)
            raise
        else:
            await ctx.message.add_reaction(ON_SUCCESS_EMOJI)

    @contextlib.asynccontextmanager
    async def remove_on_success(
        self, ticket: Ticket, *messages: discord.Message
    ) -> Generator[None, None, None]:
        """Remove provided messages from last sent messages if no errors."""
        yield
        for message in messages:
            try:
                ticket.last_sent_messages.remove(message)
            except ValueError:
                pass

    async def relay_message_to_user(
        self, ticket: Ticket, message: discord.Message, contents: str = None, *, delete: bool = True
    ) -> discord.Message:
        """Relay a message from guild to user."""
        if ticket.recipient.dm_channel is None:
            # Note, this is the recommended way by discord.py to fetch a dm channel.
            await ticket.recipient.create_dm()

        # thread -> dm
        logger.debug(
            "Relaying message id {message.id} by {message.author} "
            "from thread {thread.id} to dm channel {dm_channel.id}.".format(
                message=message, thread=ticket.thread, dm_channel=ticket.recipient.dm_channel
            )
        )

        embeds: List[Embed] = [
            Embed(
                description=contents,
                timestamp=message.created_at,
                color=message.author.color,
                author=message.author,
            )
        ]
        # make a reply if it was a reply
        dm_reference_message = None
        guild_reference_message = None
        if message.reference is not None:
            # don't error if the paired message on the server end was deleted
            message.reference.fail_if_not_exists = False
            guild_reference_message = message.reference
            try:
                dm_reference_message = ticket.messages[message.reference.message_id].to_reference(
                    fail_if_not_exists=False
                )
            except KeyError:
                pass
        if len(message.attachments) > 0:
            # don't delete when forwarding a message that has attachments,
            # as that will invalidate the attachments
            delete = False
            for a in message.attachments:
                # featuring the first image attachment as the embed image
                if a.url.lower().endswith(IMAGE_EXTENSIONS):
                    if not embeds[0].image:
                        embeds[0].set_image(url=a.url)
                        continue
                embeds[0].add_field(name=a.filename, value=a.proxy_url, inline=False)

        if len(message.stickers):
            # since users can only send one sticker right now, we only care about the first one
            sticker = await message.stickers[0].fetch()
            # IF its possible, add the sticker url to the embed attachment
            if (
                getattr(sticker, "format", discord.StickerFormatType.lottie)
                == discord.StickerFormatType.lottie
            ):
                await message.channel.send("Nope! This sticker of a type which can't be shown to the user.")
                return None
            else:
                if len(embeds[0].image) == 0:
                    embeds[0].set_image(url=sticker.url)
                else:
                    embeds.append(Embed().set_image(url=sticker.url))

        sent_message = await ticket.recipient.send(embeds=embeds, reference=dm_reference_message)
        # deep copy embeds to not have an internal race condition.
        embeds = copy.deepcopy(embeds)

        # also relay it in the thread channel
        embeds[0].set_footer(text=f"User ID: {message.author.id}")

        embeds[0].colour = INTERNAL_REPLY_COLOR
        guild_message = await ticket.thread.send(embeds=embeds, reference=guild_reference_message)

        if delete:
            await message.delete()

        # add last sent message to the list
        ticket.last_sent_messages.append(guild_message)
        if len(ticket.last_sent_messages) > MAX_CACHED_MESSAGES_PER_THREAD:
            ticket.last_sent_messages.pop(0)  # keep list length to MAX_CACHED_MESSAGES_PER_THREAD

        # add messages to the dict
        ticket.messages[guild_message] = sent_message
        return sent_message

    async def relay_message_to_guild(
        self, ticket: Ticket, message: discord.Message, contents: Optional[str] = None
    ) -> discord.Message:
        """Relay a message from user to guild."""
        if ticket.recipient.dm_channel is None:
            await ticket.recipient.create_dm()

        # dm -> thread
        logger.debug(
            "Relaying message id {message.id} from dm channel {dm_channel.id}"
            " with {message.author} to thread {thread.id}.".format(
                message=message, thread=ticket.thread, dm_channel=ticket.recipient.dm_channel
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

        embed = Embed(
            author=message.author,
            timestamp=message.created_at,
            footer_text=f"Message ID: {message.id}",
            colour=FORWARDED_DM_COLOR,
        )
        if contents is None:
            embed.description = contents = str(f"{message.content}")
        if len(message.attachments) > 0:
            attachments = message.attachments

            for a in attachments:
                if a.url.lower().endswith(IMAGE_EXTENSIONS):
                    if not embed.image:
                        embed.set_image(url=a.proxy_url)
                        continue
                embed.add_field(name=a.filename, value=a.proxy_url, inline=False)

        sticker = None
        if len(message.stickers) > 0:
            # while stickers is a list, we only care about the first one because
            # as of now, users cannot send more than one sticker in a message.
            # if this changes, we will support it.
            sticker = message.stickers[0]
            sticker = await sticker.fetch()
            # this can be one of two types of stickers, either a StandardSticker or a GuildSticker
            # StandardStickers are not usable by bots, but GuildStickers are, if they're from
            # the same guild
            if getattr(sticker, "guild_id", False) == ticket.thread.guild.id and getattr(
                sticker, "available", False
            ):
                pass
            else:

                # IF its possible, add the sticker url to the embed attachment
                if getattr(
                    sticker, "format", discord.StickerFormatType.lottie
                ) != discord.StickerFormatType.lottie and not len(embed.image):
                    embed.set_image(url=sticker.url)

                # we can't use this sticker
                if sticker.description is not None:
                    description = f"**Description:** {sticker.description.strip()}\n"
                else:
                    description = ""
                embed.add_field(
                    name="Received Sticker",
                    value=f"**Sticker**: {sticker.name}\n{description}\n[Click for file]({sticker.url})",
                    inline=False,
                )
                sticker = None

        send_kwargs = dict()
        if sticker is not None:
            send_kwargs["stickers"] = [sticker]

        if message.activity is not None:
            embed.add_field(name="Activity Sent", value="\u200b")

        if (
            0 == len(embed.description) == len(embed.image) == len(embed.fields)
            and send_kwargs.get("attachments") is None
            and send_kwargs.get("stickers") is None
        ):
            logger.info(
                f"SKIPPING relay of message id {message.id} from {message.author!s} due to nothing to relay."
            )
            return None

        sent_message = await ticket.thread.send(embed=embed, reference=guild_reference_message, **send_kwargs)

        # add messages to the dict
        ticket.messages[message] = sent_message
        return sent_message

    async def mark_thread_responded(self, ticket: Ticket) -> bool:
        """Mark thread as responded. Returns True upon success, and False if it was already marked."""
        if (log_embeds := ticket.log_message.embeds)[0].colour == NO_REPONSE_COLOUR:
            log_embeds[0].colour = HAS_RESPONSE_COLOUR
            await ticket.log_message.edit(embeds=log_embeds)
            return True
        return False

    @is_modmail_thread()
    @commands.command(aliases=("r",))
    async def reply(self, ctx: Context, *, message: str = None) -> None:
        """Send a reply to the user."""
        if message is None and not ctx.message.attachments and not ctx.message.stickers:
            param = inspect.Parameter("message", 3)
            raise commands.MissingRequiredArgument(param)
        ticket = await self.fetch_ticket(ctx.channel.id)
        if not ticket.has_sent_initial_message:
            await ctx.trigger_typing()
            logger.info(
                "Sending initial message before replying on a thread "
                "that was opened with the contact command."
            )

            await ticket.recipient.send(
                embeds=[
                    Embed(
                        title="Ticket Opened",
                        description="A moderator has opened this ticket to have a conversation with you.",
                    )
                ]
            )
            ticket.has_sent_initial_message = True

            await asyncio.sleep(1)

        await self.relay_message_to_user(ticket, ctx.message, message)

        await self.mark_thread_responded(ticket)

    @is_modmail_thread()
    @commands.command(aliases=("e", "ed"))
    @commands.max_concurrency(1, commands.BucketType.channel, wait=True)
    async def edit(
        self, ctx: Context, message: RepliedOrRecentMessageConverter(optional=True) = None, *, content: str
    ) -> None:
        """
        Edit a message in the thread.

        If the message is a reply and no message is provided, the bot will attempt to use the replied message.
        However, if the reply is *not* to the bot, no action is taken.

        If there is no reply or message provided, the bot will edit the last sent message.
        """
        if message is None:
            message, err = await RepliedOrRecentMessageConverter().convert(ctx, "")
        else:
            message, err = message

        if err is not None:
            raise err

        ticket = await self.fetch_ticket(ctx.channel.id)

        # process and get proper message
        messages = await self.resolve_mirror_message_for_manipulation(
            ctx,
            ticket,
            message,
        )

        if messages is None:
            return

        user_message, message = messages

        async with self.handle_success(ctx):
            # edit user message
            embed = user_message.embeds[0]
            embed.description = content
            await user_message.edit(embed=embed)

            # edit guild message
            embed = message.embeds[0]
            embed.description = content
            await message.edit(embed=embed)

    @is_modmail_thread()
    @commands.command(aliases=("d", "del"))
    @commands.max_concurrency(1, commands.BucketType.channel, wait=True)
    async def delete(
        self,
        ctx: Context,
        message: RepliedOrRecentMessageConverter(require_argument_empty=True) = None,
    ) -> None:
        """
        Delete a message in the thread.

        If the message is a reply and no message is provided, the bot will attempt to use the replied message.
        However, if the reply is *not* to the bot, no action is taken.

        If there is no reply or message provided, the bot will delete the last sent message.
        """
        if message is None:
            message, err = await RepliedOrRecentMessageConverter().convert(ctx, "")
        else:
            message, err = message

        if err is not None:
            raise err

        ticket = await self.fetch_ticket(ctx.channel.id)

        # process and get proper message
        messages = await self.resolve_mirror_message_for_manipulation(
            ctx,
            ticket,
            message,
        )

        if messages is None:
            return

        dm_message, thread_message = messages

        async with self.handle_success(ctx):
            async with self.remove_on_success(ticket, thread_message):
                self.dm_deleted_messages.add(dm_message.id)
                await dm_message.delete()

                self.thread_deleted_messages.add(thread_message.id)
                await thread_message.delete()

    async def close_thread(
        self,
        ticket: Ticket,
        closer: Optional[Union[discord.User, discord.Member]] = None,
        time: Optional[datetime.datetime] = None,
        notify_user: Optional[bool] = None,
        automatically_archived: bool = False,
        *,
        contents: str = None,
        keep_thread_closed: bool = False,
    ) -> None:
        """
        Close the current thread after `after` time from now.

        Note: This method destroys the Ticket object.

        If keep_thread_closed is True, this method will not send any messages in the thread,
        since that would re-open the thread.
        """
        if notify_user is None:
            notify_user = bool(ticket.has_sent_initial_message or len(ticket.messages) > 0)

        if closer:
            thread_close_embed = discord.Embed(
                title="Thread Closed",
                description=contents or f"{closer.mention} has closed this Modmail thread.",
                timestamp=arrow.utcnow().datetime,
            )
        else:
            thread_close_embed = discord.Embed(
                title="Thread Closed",
                description=contents or "This thread has been closed.",
                timestamp=arrow.utcnow().datetime,
            )

        async with self.thread_create_delete_lock:
            # clean up variables
            if not keep_thread_closed:
                await ticket.thread.send(embed=thread_close_embed)
            if notify_user:
                # user may have dms closed
                try:
                    await ticket.recipient.send(embed=thread_close_embed)
                except discord.HTTPException:
                    logger.debug(f"{ticket.recipient} is unable to be DMed. Skipping.")
                    pass

            try:
                del self.bot._tickets[ticket.thread.id]
                del self.bot._tickets[ticket.recipient.id]
            except KeyError:
                logger.warning("Ticket not found in tickets dict when attempting removal.")
            # ensure we get rid of the ticket messages, as this can be an extremely large dict
            else:
                # remove the user's dm channel from the dict
                try:
                    del self.dms_to_users[ticket.recipient.dm_channel.id]
                except KeyError:
                    # not a problem if the user is already removed
                    pass

            del ticket.messages

        if (log_embeds := ticket.log_message.embeds)[0].colour != CLOSED_COLOUR:
            log_embeds[0].colour = CLOSED_COLOUR
            await ticket.log_message.edit(embeds=log_embeds)

        await ticket.thread.edit(archived=True, locked=False)

        if not closer:
            logger.debug(f"{closer!s} has closed thread {ticket.thread!s}.")
        else:
            logger.debug(f"{ticket.thread!s} has been closed. A user was not provided.")

    @is_modmail_thread()
    @commands.group(invoke_without_command=True)
    async def close(self, ctx: Context, *, contents: str = None) -> None:
        """Close the current thread after `after` time from now."""
        # TODO: Implement after duration
        ticket = await self.fetch_ticket(ctx.channel.id)
        if ticket is None:
            await ctx.send("Error: this thread is not in the list of tickets.")
            return

        await self.close_thread(ticket, ctx.author, contents=contents)

    @ModmailCog.listener(name="on_message")
    async def on_dm_message(self, message: discord.Message) -> None:
        """Relay all dms to a thread channel."""
        author = message.author

        if author.id == self.bot.user.id:
            return

        if message.guild:
            return

        ticket = await self.fetch_ticket(author.id)
        if ticket is None:
            # Thread doesn't exist, so create one.
            async with self.thread_create_lock:
                try:
                    ticket = await self.create_ticket(message, raise_for_preexisting=True)
                except ThreadAlreadyExistsError:
                    # the thread already exists, so we still need to relay the message
                    # thankfully a keyerror should NOT happen now
                    ticket = await self.fetch_ticket(author.id)
                    msg = await self.relay_message_to_guild(ticket, message)
                else:
                    msg = await self.relay_message_to_guild(ticket, message)
                    if msg is None:
                        return
                    await message.channel.send(
                        embeds=[
                            Embed(
                                title="Ticket Opened",
                                description=f"Thanks for dming {self.bot.user.name}! "
                                "A member of our staff will be with you shortly!",
                                timestamp=message.created_at,
                            )
                        ]
                    )
        else:
            msg = await self.relay_message_to_guild(ticket, message)
            if msg is None:
                return

        await message.add_reaction(ON_SUCCESS_EMOJI)

    @ModmailCog.listener(name="on_raw_message_edit")
    async def on_dm_message_edit(self, payload: discord.RawMessageUpdateEvent) -> None:
        """
        Receive a dm message edit, and edit the message in the channel.

        In the future, this will be expanded to use a modified paginator.
        """
        if payload.guild_id is not None:
            return

        if payload.data["author"]["id"] == self.bot.user.id:
            return

        logger.trace(
            f'User ID {payload.data["author"]["id"]} has edited a message '
            f"in their dms with id {payload.message_id}"
        )
        ticket = await self.fetch_ticket(int(payload.data["author"]["id"]))
        if ticket is None:
            logger.debug(
                f"User {payload.data['author']['id']} edited a message in dms which "
                "was related to a non-existant ticket."
            )
            return

        guild_msg = ticket.messages[payload.message_id]

        new_embed = guild_msg.embeds[0]

        data = payload.data
        if data.get("content") is not None:
            new_embed.insert_field_at(0, name="Former contents", value=new_embed.description)
            new_embed.description = data["content"]

        await guild_msg.edit(embed=new_embed)

        dm_channel = self.bot.get_partial_messageable(payload.channel_id, type=discord.DMChannel)
        await dm_channel.send(
            embed=discord.Embed(
                "Successfully edited message.",
                footer_text=f"Message ID: {payload.message_id}",
            ),
            reference=discord.MessageReference(message_id=payload.message_id, channel_id=payload.channel_id),
        )

    @ModmailCog.listener(name="on_raw_message_delete")
    async def on_dm_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        """
        Receive a dm message edit, and edit the message in the channel.

        In the future, this will be expanded to use a modified paginator.
        """
        if payload.guild_id is not None:
            return

        if payload.message_id in self.dm_deleted_messages:
            logger.debug(f"Ignoring message deleted by self in {payload.channel_id}")
            self.dm_deleted_messages.remove(payload.message_id)
            return

        try:
            # get the user id
            author_id = self.dms_to_users[payload.channel_id]
        except KeyError:
            channel: discord.DMChannel = await self.bot.fetch_channel(payload.channel_id)
            author_id = channel.recipient.id
            # add user to dict
            self.dms_to_users[payload.channel_id] = author_id

        logger.trace(
            f"A message from {author_id} in dm channel {payload.channel_id} has "
            f"been deleted with id {payload.message_id}."
        )
        ticket = await self.fetch_ticket(author_id)
        if ticket is None:
            logger.debug(
                f"User {author_id} edited a message in dms which was related to a non-existant ticket."
            )
            return

        guild_msg = ticket.messages[payload.message_id]

        new_embed = guild_msg.embeds[0]

        new_embed.colour = discord.Colour.red()
        new_embed.insert_field_at(
            0, name="Deleted", value=f"Deleted at {get_discord_formatted_timestamp(arrow.utcnow())}"
        )
        await guild_msg.edit(embed=new_embed)

        dm_channel = self.bot.get_partial_messageable(payload.channel_id, type=discord.DMChannel)
        await dm_channel.send(embed=discord.Embed("Successfully deleted message."))

    @ModmailCog.listener(name="on_raw_message_delete")
    async def on_thread_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        """Automatically deletes a message in the dms if it was deleted on the moderator end."""
        if payload.guild_id is None:
            return

        if payload.message_id in self.thread_deleted_messages:
            self.thread_deleted_messages.remove(payload.message_id)
            logger.debug(
                f"SKIPPING mirror of deleted message {payload.message_id} since it was deleted via a command."
            )
            return

        ticket = await self.fetch_ticket(payload.channel_id)
        if ticket is None:
            # not a valid ticket
            return

        if ticket.thread.id != payload.channel_id:
            logger.warn("I have no idea what happened. This is a good time to stop using the bot.")
            return

        try:
            dm_msg = ticket.messages[payload.message_id]
        except KeyError:
            # message was deleted as a command
            return

        logger.info(
            f"Relaying manual message deletion in {payload.channel_id} to {ticket.recipient.dm_channel}"
        )
        self.dm_deleted_messages.add(dm_msg.id)
        await dm_msg.delete()

    @ModmailCog.listener(name="on_typing")
    async def on_typing(
        self,
        channel: discord.abc.Messageable,
        user: Union[discord.User, discord.Member],
        _: datetime.datetime,
    ) -> None:
        """Relay typing events to the thread channel."""
        if user.id == self.bot.user.id:
            return

        # only work in dms or a thread channel

        if FORWARD_MODERATOR_TYPING and isinstance(channel, discord.Thread):

            ticket = await self.fetch_ticket(channel.id)
            if ticket is None:
                # Thread doesn't exist, so there's nowhere to relay the typing event.
                return
            logger.debug(f"Relaying typing event from {user!s} in {channel!s} to {ticket.recipient!s}.")
            await ticket.recipient.trigger_typing()

        # ! Due to a library bug this tree will never be run
        # it can be tracked here: https://github.com/Rapptz/discord.py/issues/7432
        elif FORWARD_USER_TYPING and isinstance(channel, discord.DMChannel):
            ticket = await self.fetch_ticket(user.id)
            if ticket is None:
                # User doesn't have a ticket, so nowhere to relay the event.
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
        # while this should never change, I'm using `before` in case for some reason
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

        if archiver is None:
            # check the last message id
            now = arrow.utcnow().datetime
            last_message_time = discord.Object(after.last_message_id).created_at
            print()
            if before.auto_archive_duration <= (now - last_message_time).total_seconds():
                # thread was automatically archived, probably.
                automatically_archived = True

        # checks passed, closing the ticket
        ticket = await self.fetch_ticket(after.id)
        if ticket is None:
            logger.debug(
                "While closing a ticket, somehow checks passed but the thread did not exist... "
                "This is likely due to missing audit log permissions."
            )
            return

        await self.close_thread(ticket, archiver, automatically_archived=automatically_archived)

    @is_modmail_thread()
    @commands.command(name="debug_thread", enabled=DEV_MODE_ENABLED)
    async def debug(self, ctx: Context, attr: str = None) -> None:
        """Debug command. Requires a message reference (reply)."""
        ticket = await self.fetch_ticket(ctx.channel.id)
        if ticket is None:
            await ctx.send("no ticket found associated with this channel.")
            return
        dm_msg = ticket.messages[ctx.message.reference.message_id]

        if attr is None:
            attribs: Dict[str] = {}
            longest_len = 0
            for attr in dir(dm_msg):
                if attr.startswith("_"):
                    continue
                thing = getattr(dm_msg, attr)
                if callable(thing):
                    continue
                attribs[attr] = thing
                if len(attr) > longest_len:
                    longest_len = len(attr)

            con = ""
            longest_len += 2
            for k, v in attribs.items():
                con += f"{k.rjust(longest_len, ' ')}: {v!r}\n"

        else:
            con = getattr(dm_msg, attr, "UNSET")
        await ctx.send(f"```py\n{con}```")

    async def cog_command_error(self, ctx: Context, error: commands.CommandError) -> None:
        """Ignore all dm command errors since commands are not allowed in dms."""
        if isinstance(error, commands.CheckFailure) and isinstance(ctx.channel, discord.DMChannel):
            error.handled = True


def setup(bot: "ModmailBot") -> None:
    """Adds the Tickets cog to the bot."""
    bot.add_cog(TicketsCog(bot))
