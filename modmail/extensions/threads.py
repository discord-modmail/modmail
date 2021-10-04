import asyncio
import datetime
import inspect
import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple, Union

import discord
from arrow import Arrow
from discord import Embed
from discord.ext import commands, tasks
from discord.ext.commands import Context, Greedy
from discord.utils import escape_markdown

from modmail.utils.cogs import ExtMetadata, ModmailCog
from modmail.utils.converters import Duration
from modmail.utils.extensions import BOT_MODE, BotModes
from modmail.utils.threads import Ticket, is_modmail_thread
from modmail.utils.threads.errors import ThreadAlreadyExistsError, ThreadNotFoundError
from modmail.utils.users import check_can_dm_user


if TYPE_CHECKING:
    from modmail.bot import ModmailBot
    from modmail.log import ModmailLogger

EXT_METADATA = ExtMetadata()

DEV_MODE_ENABLED = BOT_MODE & BotModes.DEVELOP

BASE_JUMP_URL = "https://discord.com/channels"
USER_NOT_ABLE_TO_BE_DMED_MESSAGE = (
    "**{0}** is not able to be DMed! This is because they have either blocked the bot, "
    "or they are only accepting direct messages from friends.\n"
    "It is also possible that they do not share a server with the bot"
)
ON_SUCCESS_EMOJI = "\u2705"  # ✅
FAILURE_EMOJI = "\u274c"  # :x:

# This will be part of configuration later, so its stored in globals for now
ENABLE_DM_TO_GUILD_TYPING = False  # Library bug prevents this form working right now
ENABLE_GUILD_TO_DM_TYPING = False

# NOTE: Since discord removed `threads.archiver_id`, it would always be `None`, and the
# only way to get the user who archived the thread is to use the Audit logs.
# however, this permission is not required to have basic functionality.
# this permission
USE_AUDIT_LOGS = True

NO_REPONSE_COLOUR = discord.Colour.red()
HAS_RESPONSE_COLOUR = discord.Colour.yellow()
CLOSED_COLOUR = discord.Colour.green()

logger: "ModmailLogger" = logging.getLogger(__name__)


class TicketsCog(ModmailCog, name="Threads"):
    """A cog for relaying direct messages."""

    def __init__(self, bot: "ModmailBot"):
        self.bot = bot
        self.relay_channel: Union[
            discord.TextChannel, discord.PartialMessageable
        ] = self.bot.get_partial_messageable(self.bot.config.thread.relay_channel_id)

        # message deletion events are messed up
        self.dms_to_users: Dict[int, int] = dict()
        self.dm_deleted_messages: Set[int] = set()
        self.thread_deleted_messages: Set[int] = set()

        self.thread_create_delete_lock = asyncio.Lock()
        self.thread_create_lock = asyncio.Lock()

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
            raise ThreadNotFoundError(f"Could not find thread from id {id}.") from None
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
        self,
        ctx: Context,
        recipient: Union[discord.User, discord.Member],
        *,
        reason: str = "",
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
                    raise_for_preexisting_ticket=True,
                    send_initial_message=False,
                    description=reason,
                    creator=ctx.message.author,
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
        raise_for_preexisting_ticket: bool = True,
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
            if recipient.id in self.bot.tickets.keys():
                if raise_for_preexisting_ticket:
                    raise ThreadAlreadyExistsError(recipient.id)
                else:
                    return self.bot.tickets[recipient.id]

            thread_channel, thread_msg = await self._start_discord_thread(
                initial_message,
                recipient,
                description=description,
                creator=creator,
            )
            ticket = Ticket(
                recipient,
                thread_channel,
                has_sent_initial_message=send_initial_message,
                log_message=thread_msg,
            )
            # add the ticket as both the recipient and the thread ids so
            # the tickets can be retrieved from both users or threads.
            self.bot.tickets[recipient.id] = ticket
            self.bot.tickets[thread_channel.id] = ticket

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
        """
        await self.init_relay_channel()

        send_kwargs = {}
        if recipient is None:
            recipient = message.author
        if send_kwargs.get("allowed_mentions", None) is not None:
            send_kwargs["allowed_mentions"] = discord.AllowedMentions(
                everyone=False, users=False, roles=True, replied_user=False
            )
        if self.bot.config.thread.thread_mention_role_id is not None:
            mention = f"<@&{self.bot.config.thread.thread_mention_role_id}>"
        else:
            mention = "@here"

        if description is None:
            description = message.content
        description = description.strip()
        description += f"\n\nOpened <t:{int(datetime.datetime.now().timestamp())}:R>"
        if creator:
            description += f" by {creator!s}"

        embed = discord.Embed(
            title=f"{discord.utils.escape_markdown(recipient.name,ignore_links=False)}"
            f"#{recipient.discriminator} (`{recipient.id}`)",
            description=f"{description}",
            timestamp=datetime.datetime.now(),
            color=NO_REPONSE_COLOUR,
        )
        relayed_msg = await self.relay_channel.send(
            content=mention,
            embed=embed,
            **send_kwargs,
        )
        thread_channel = await relayed_msg.create_thread(
            name=str(recipient.name + "-" + recipient.discriminator),
            auto_archive_duration=relayed_msg.channel.default_auto_archive_duration,
        )

        return thread_channel, relayed_msg

    async def _relay_message_to_user(
        self, ticket: Ticket, message: discord.Message, contents: str = None, *, delete: bool = True
    ) -> discord.Message:
        """Relay a message from guild to user."""
        if ticket.recipient.dm_channel is None:
            await ticket.recipient.create_dm()

        # thread -> dm
        logger.debug(
            "Relaying message id {0} by {3} from thread {1} to dm channel {2}.".format(
                message.id, ticket.thread.id, ticket.recipient.dm_channel.id, message.author
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
            # don't want to fail a reference
            message.reference.fail_if_not_exists = False
            guild_reference_message = message.reference
            try:
                dm_reference_message = ticket.messages[message.reference.message_id].to_reference(
                    fail_if_not_exists=False
                )
            except KeyError:
                pass
        if len(message.attachments) > 0:
            delete = False
            for a in message.attachments:
                if a.url.endswith((".png", ".apng", ".gif", ".webm", "jpg", ".jpeg")):
                    if not len(embeds[0].image):
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

        # also relay it in the thread channel
        embeds[0].set_footer(text=f"User ID: {message.author.id}")
        guild_message = await ticket.thread.send(embeds=embeds, reference=guild_reference_message)

        if delete:
            await message.delete()

        # add last sent message to the list
        ticket.last_sent_messages.append(guild_message)
        if len(ticket.last_sent_messages) > 10:
            ticket.last_sent_messages.pop(0)  # keep list length to 10

        # add messages to the dict
        ticket.messages[guild_message] = sent_message
        return sent_message

    async def _relay_message_to_guild(
        self, ticket: Ticket, message: discord.Message, contents: str = None
    ) -> discord.Message:
        """Relay a message from user to guild."""
        if ticket.recipient.dm_channel is None:
            await ticket.recipient.create_dm()

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

        embed = Embed(
            author=message.author,
            timestamp=message.created_at,
            footer_text=f"Message ID: {message.id}",
        )
        if contents is None:
            embed.description = contents = str(f"{message.content}")
        if len(message.attachments) > 0:
            attachments = message.attachments

            for a in attachments:
                if a.url.endswith((".png", ".apng", ".gif", ".webm", "jpg", ".jpeg")):
                    if not len(embed.image):
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

        kw = dict()
        if sticker is not None:
            kw["stickers"] = [sticker]

        if message.activity is not None:
            embed.add_field(name="Activity Sent", value="\u200b")

        if (
            0 == len(embed.description) == len(embed.image) == len(embed.fields)
            and kw.get("attachments", None) is None
            and kw.get("stickers", None) is None
        ):
            logger.info(
                f"SKIPPING relay of message id {message.id} from {message.author!s} due to nothing to relay."
            )
            return None

        sent_message = await ticket.thread.send(embed=embed, reference=guild_reference_message, **kw)

        # add messages to the dict
        ticket.messages[message] = sent_message
        return sent_message

    @is_modmail_thread()
    @commands.command(aliases=("r",))
    async def reply(self, ctx: Context, *, message: str = None) -> None:
        """Send a reply to the user."""
        if message is None and 0 == len(ctx.message.attachments) == len(ctx.message.stickers):
            param = inspect.Parameter("message", 3)
            raise commands.MissingRequiredArgument(param)
        ticket = self.get_ticket(ctx.channel.id)
        if not ticket.has_sent_initial_message:
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

            await ctx.trigger_typing()
            await asyncio.sleep(1)

        await self._relay_message_to_user(ticket, ctx.message, message)

        if (log_embeds := ticket.log_message.embeds)[0].colour == NO_REPONSE_COLOUR:
            log_embeds[0].colour = HAS_RESPONSE_COLOUR
            await ticket.log_message.edit(embeds=log_embeds)

    @is_modmail_thread()
    @commands.command(aliases=("e",))
    async def edit(self, ctx: Context, message: Optional[discord.Message] = None, *, content: str) -> None:
        """Edit a message in the thread."""
        ticket = self.get_ticket(ctx.channel.id)

        if message is None:
            if ctx.message.reference is not None:
                ref = ctx.message.reference
                message = ref.resolved or await ctx.channel.fetch_message(ref.message_id)

                if message.author.id != self.bot.user.id:
                    logger.info(
                        "Edit command contained a reply, but was not to one of my messages so skipping."
                    )
                    return

                # remove from last sent
                try:
                    ticket.last_sent_messages.remove(message)
                except ValueError:
                    pass

            else:
                try:
                    message = ticket.last_sent_messages[-1]
                except IndexError:
                    await ctx.send("There's no message here to edit!")
                    return

        # edit user message
        try:
            user_message = ticket.messages[message]
        except KeyError:
            await ctx.send(
                "Sorry, this is not a message that I can edit.",
                reference=message.to_reference(fail_if_not_exists=False),
            )
            return
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
    async def delete(
        self, ctx: Context, messages: Greedy[discord.Message] = None, *, reason: str = None
    ) -> None:
        """
        Delete a message in the thread.

        If the message is a reply and no message is provided, the bot will attempt to use the replied message.
        However, if the reply is *not* to the bot, the last message will be used.
        """
        ticket = self.get_ticket(ctx.channel.id)
        if messages is None:
            if ctx.message.reference is not None:
                logger.debug(
                    "Message param was not provided on the delete command, but a reference was provided. "
                    "Checking if reference is one of my messages."
                )
                ref = ctx.message.reference
                message = ref.resolved or await ctx.channel.fetch_message(ref.message_id)
                if message.author.id != self.bot.user.id:
                    logger.info(
                        "Delete command contained a reply, but was not to one of my messages so skipping."
                    )
                    return

                # remove from last sent
                try:
                    ticket.last_sent_messages.remove(message)
                except ValueError:
                    pass

            else:
                try:
                    message = ticket.last_sent_messages.pop()
                except IndexError:
                    await ctx.send("There's no message here to delete!")
                    return

            messages = [message]

        # delete multiple messages
        dm_messages: List[discord.Message] = []
        message_count = len(messages)
        for message in messages.copy():
            try:
                if message.channel != ctx.channel:
                    raise KeyError
                msg = ticket.messages[message]

                if msg.author != self.bot.user:
                    raise KeyError
                dm_messages.append(ticket.messages[message])

            except KeyError:
                if message_count >= 2:
                    messages.remove(message)
                else:
                    await ctx.send(
                        "Sorry, I cannot delete this message.",
                        reference=message.to_reference(fail_if_not_exists=False),
                    )
                    return

        for msg in dm_messages:
            self.dm_deleted_messages.add(msg.id)
            await msg.delete()

        for msg in messages:
            self.thread_deleted_messages.add(msg.id)

        await ctx.channel.delete_messages(messages)

        if len(messages) > 0:
            await ctx.message.add_reaction(ON_SUCCESS_EMOJI)
        else:
            await ctx.message.add_reaction(FAILURE_EMOJI)

    async def _close_thread(
        self,
        ticket: Ticket,
        closer: Optional[Union[discord.User, discord.Member]] = None,
        time: Optional[datetime.datetime] = None,
        discord_thread_already_archived: bool = False,
        notify_user: Optional[bool] = None,
        automatically_archived: bool = False,
        *,
        contents: str = None,
    ) -> None:
        """
        Close the current thread after `after` time from now.

        Note: This method destroys the Ticket object.
        """
        if notify_user is None:
            notify_user = bool(ticket.has_sent_initial_message or len(ticket.messages) > 0)

        if closer is not None:
            thread_close_embed = discord.Embed(
                title="Thread Closed",
                description=contents or f"{closer.mention} has closed this Modmail thread.",
                timestamp=Arrow.utcnow().datetime,
            )
        else:
            thread_close_embed = discord.Embed(
                title="Thread Closed",
                description=contents or "This thread has been closed.",
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
                    logger.debug(f"{ticket.recipient} is unable to be DMed. Skipping.")
                    pass

            try:
                del self.bot.tickets[ticket.thread.id]
                del self.bot.tickets[ticket.recipient.id]
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

        if closer is not None:
            logger.debug(f"{closer!s} has closed thread {ticket.thread!s}.")
        else:
            logger.debug(f"{ticket.thread!s} has been closed. A user was not provided.")

    @is_modmail_thread()
    @commands.group(invoke_without_command=True)
    async def close(self, ctx: Context, _: Optional[Duration] = None, *, contents: str = None) -> None:
        """Close the current thread after `after` time from now."""
        # TODO: Implement after duration
        try:
            ticket = self.bot.tickets[ctx.channel.id]
        except KeyError:
            await ctx.send("Error: this thread is not in the list of tickets.")
            return

        await self._close_thread(ticket, ctx.author, contents=contents)

    @ModmailCog.listener(name="on_message")
    async def on_dm_message(self, message: discord.Message) -> None:
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
            async with self.thread_create_lock:
                try:
                    ticket = await self.create_ticket(message, raise_for_preexisting_ticket=True)
                except ThreadAlreadyExistsError:
                    # the thread already exists, so we still need to relay the message
                    # thankfully a keyerror should NOT happen now
                    ticket = self.bot.tickets[author.id]
                    msg = await self._relay_message_to_guild(ticket, message)
                else:
                    msg = await self._relay_message_to_guild(ticket, message)
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
            msg = await self._relay_message_to_guild(ticket, message)
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

        if payload.data.get("embeds") is not None:
            return

        logger.trace(
            f'User ID {payload.data["author"]["id"]} has edited a message '
            f"in their dms with id {payload.message_id}"
        )
        try:
            ticket = self.get_ticket(int(payload.data["author"]["id"]))
        except ThreadNotFoundError:
            logger.debug(
                f"User {payload.data['author']['id']} edited a message in dms which "
                "was related to a non-existant ticket."
            )
            return

        guild_msg = ticket.messages[payload.message_id]

        new_embed = guild_msg.embeds[0]

        data = payload.data
        if data.get("content", None) is not None:
            new_embed.insert_field_at(0, name="Former contents", value=new_embed.description)
            new_embed.description = data["content"]

        await guild_msg.edit(embed=new_embed)

        dm_channel = self.bot.get_partial_messageable(payload.channel_id, type=discord.DMChannel)
        await dm_channel.send(
            embed=discord.Embed("Successfully edited message."),
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
            channel = await self.bot.fetch_channel(payload.channel_id)
            author_id = channel.recipient.id
            # add user to dict
            self.dms_to_users[payload.channel_id] = author_id

        logger.trace(
            f"A message from {author_id} in dm channel {payload.channel_id} has "
            f"been deleted with id {payload.message_id}."
        )
        try:
            ticket = self.get_ticket(author_id)
        except ThreadNotFoundError:
            logger.debug(
                f"User {author_id} edited a message in dms which was related to a non-existant ticket."
            )
            return

        guild_msg = ticket.messages[payload.message_id]

        new_embed = guild_msg.embeds[0]

        new_embed.colour = discord.Colour.red()
        new_embed.insert_field_at(0, name="Deleted", value=f"Deleted at <t:{Arrow.utcnow().int_timestamp}:f>")
        await guild_msg.edit(embed=new_embed)

        dm_channel = self.bot.get_partial_messageable(payload.channel_id, type=discord.DMChannel)
        await dm_channel.send(
            embed=discord.Embed("Successfully deleted message."),
        )

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

        try:
            ticket = self.get_ticket(payload.channel_id)
        except ThreadNotFoundError:
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

    @is_modmail_thread()
    @commands.command(name="debug_thread", enabled=DEV_MODE_ENABLED)
    async def debug(self, ctx: Context, attr: str = None) -> None:
        """Debug command. Requires a message reference (reply)."""
        tick = self.get_ticket(ctx.channel.id)
        dm_msg = tick.messages[ctx.message.reference.message_id]

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


def setup(bot: "ModmailBot") -> None:
    """Adds the Tickets cog to the bot."""
    bot.add_cog(TicketsCog(bot))
