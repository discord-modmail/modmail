import typing
import unittest.mock
from typing import TYPE_CHECKING

import arrow
import discord
import pytest

from modmail.extensions import threads
from modmail.utils import threads as thread_utils
from tests import mocks


if TYPE_CHECKING:  # pragma: nocover
    from modmail.bot import ModmailBot

GUILD_ID = mocks.generate_realistic_id()


def _get_fake_ticket():
    guild = mocks.MockGuild(id=GUILD_ID)
    channel = mocks.MockTextChannel(guild=guild)
    user = mocks.MockUser()
    thread = mocks.MockThread(guild=guild)
    thread.parent = channel
    message = mocks.MockMessage(guild=guild, channel=channel)

    ticket = thread_utils.Ticket(user, thread, log_message=message)
    return ticket


@pytest.fixture()
def ticket():
    """Fixture for ticket generation."""
    return _get_fake_ticket()


@pytest.fixture()
def ticket_dict():
    """Create a dictionary with some fake tickets in it."""
    ticket_dict: typing.Dict[int, thread_utils.Ticket] = dict()
    for _ in range(2):
        tick = _get_fake_ticket()
        ticket_dict[tick.recipient.id] = tick
        ticket_dict[tick.thread.id] = tick

    return ticket_dict


@pytest.fixture()
def bot():
    """
    Fixture for mock bot.

    A few attributes on the bot are set to actual objects instead of remaining as mocks.
    """
    bot: ModmailBot = mocks.MockBot()
    bot._tickets = dict()
    return bot


@pytest.fixture()
def cog(bot):
    """Fixture of a TicketsCog to make testing easier."""
    cog = threads.TicketsCog(bot)
    yield cog
    cog.cog_unload()


class TestUtilityMethods:
    """Test utility methods of the cog that don't fit anywhere else."""

    @pytest.mark.asyncio
    async def test_add_ticket(self, cog: threads.TicketsCog, ticket: threads.Ticket):
        """Ensure that add ticket adds the ticket to the dictionary on both sides, like a MessageDict."""
        bot = cog.bot
        ticket_copy = await cog.add_ticket(ticket)

        assert ticket_copy is ticket

        assert ticket in bot._tickets.values()
        assert ticket.recipient.id in bot._tickets.keys()
        assert ticket.thread.id in bot._tickets.keys()

        assert bot._tickets[ticket.thread.id] == ticket
        assert bot._tickets[ticket.recipient.id] == ticket

    @pytest.mark.asyncio
    async def test_get_ticket(self, bot, cog: threads.TicketsCog, ticket: threads.Ticket):
        """Ensure that get_tickets returns the correct ticket."""
        bot._tickets = dict()
        await cog.add_ticket(ticket)
        received_ticket = await cog.fetch_ticket(ticket.thread.id)
        assert ticket is received_ticket
        del received_ticket

        received_ticket = await cog.fetch_ticket(ticket.recipient.id)
        assert ticket is received_ticket

    @pytest.mark.asyncio
    async def test_invalid_get_ticket(self, cog: threads.TicketsCog, ticket_dict: dict):
        """Test invalid get_ticket ids raise a ThreadNotFoundError."""
        cog.bot._tickets = ticket_dict

        with pytest.raises(threads.ThreadNotFoundError):
            await cog.fetch_ticket(mocks.generate_realistic_id())

    # TODO: More tests for this method
    @pytest.mark.asyncio
    async def test_create_ticket(self, bot: "ModmailBot", cog: threads.TicketsCog, ticket: threads.Ticket):
        """Test the create_ticket method adds the ticket to the internal dictionary."""
        # this method uses a mock ticket since the ticket already has thread, user, log_message.
        msg = mocks.MockMessage(guild=None, author=ticket.recipient)

        # patch start discord thread
        mock_start_thread_response = (ticket.thread, ticket.log_message)
        with unittest.mock.patch.object(
            cog, "_start_discord_thread", return_value=mock_start_thread_response
        ) as mock_start_discord_thread:
            returned_ticket = await cog.create_ticket(msg)

        assert 1 == mock_start_discord_thread.call_count
        assert msg == mock_start_discord_thread.call_args[0][0]
        assert ticket.recipient == mock_start_discord_thread.call_args[0][1]

        assert ticket.thread is returned_ticket.thread
        assert ticket.recipient is returned_ticket.recipient

        assert ticket.thread.id in bot._tickets.keys()
        assert ticket.recipient.id in bot._tickets.keys()
        assert returned_ticket in bot._tickets.values()

    # TODO: write more tests for this specific method
    @pytest.mark.asyncio
    async def test_start_discord_thread(self, bot, cog: threads.TicketsCog, ticket: threads.Ticket):
        """Test _start_discord_thread does what it says and returns the correct thread and message."""
        cog.relay_channel = mocks.MockTextChannel()
        user = mocks.MockUser(name="NitroScammer")
        thread = ticket.thread
        msg = mocks.MockMessage(guild=None, author=user)
        relayed_msg = mocks.MockMessage(guild=thread.guild, channel=cog.relay_channel)
        cog.relay_channel.send = unittest.mock.AsyncMock(return_value=relayed_msg)
        relayed_msg.create_thread = unittest.mock.AsyncMock(return_value=thread)

        with unittest.mock.patch.object(cog, "init_relay_channel"):
            result = await cog._start_discord_thread(msg)

        assert 2 == len(result)
        assert thread is result[0]
        assert relayed_msg is result[1]

        assert 1 == cog.relay_channel.send.call_count
        assert 1 == relayed_msg.create_thread.call_count

        assert str(user) == relayed_msg.create_thread.call_args[1]["name"]


@pytest.fixture
def ctx():
    """Mock ctx fixture."""
    return mocks.MockContext()


class TestContactCommand:
    """Test the contact command which will create a ticket with a specified user."""

    @pytest.mark.asyncio
    async def test_contact(self, ctx, bot, cog, ticket):
        """Test a contact command succeeds and creates a thread if everything is accurate."""
        user = mocks.MockUser(name="spammer")
        with unittest.mock.patch.object(cog, "create_ticket", return_value=ticket) as mock_create_ticket:
            with unittest.mock.patch.object(
                threads, "check_can_dm_user", return_value=True
            ) as mock_check_can_dm_user:
                await cog.contact(cog, ctx, user)

        assert 0 == ticket.thread.send.call_count
        assert 1 == mock_create_ticket.call_count
        assert 1 == mock_check_can_dm_user.call_count

        mock_create_ticket.assert_called_once_with(
            ctx.message,
            recipient=user,
            raise_for_preexisting=True,
            send_initial_message=False,
            description="",
            creator=ctx.message.author,
        )

    @pytest.mark.asyncio
    async def test_does_not_allow_bots(self, ctx, bot, cog):
        """Properly notify the user that tickets cannot be started with other bots."""
        user = mocks.MockUser(name="defintely a human", bot=True)
        await cog.contact(cog, ctx, user)
        assert 1 == ctx.send.call_count
        assert "bot" in ctx.send.call_args[0][0]

        ctx.reset_mock()

        await cog.contact(cog, ctx, bot.user)
        assert 1 == ctx.send.call_count
        assert "perfect" in ctx.send.call_args[0][0]

    @pytest.mark.asyncio
    async def test_ticket_already_exists(self, ctx, bot, cog, ticket):
        """Send an alert to the user if the thread already exists."""
        user = mocks.MockUser(name="spammer")
        with unittest.mock.patch.object(
            cog, "create_ticket", side_effect=threads.ThreadAlreadyExistsError()
        ) as mock_create_ticket:
            with unittest.mock.patch.object(cog, "fetch_ticket", return_value=ticket):
                await cog.contact(cog, ctx, user)
        thread = ticket.thread
        assert 0 == ticket.thread.send.call_count
        assert 1 == ctx.send.call_count
        assert 1 == mock_create_ticket.call_count

        sent_content = ctx.send.call_args[0][0]
        important_info = [
            "already exists",
            user.mention,
            user.id,
            f"{threads.BASE_JUMP_URL}/{thread.guild.id}/{thread.id}",
        ]
        for item in important_info:
            assert str(item) in sent_content

    @pytest.mark.asyncio
    async def test_check_can_dm_user_false(self, ctx, bot, cog, ticket):
        """Check if the thread is notified if a user is unable to be dmed upon creation."""
        user = mocks.MockUser(name="spammer", discriminator="5555")
        with unittest.mock.patch.object(cog, "create_ticket", return_value=ticket) as mock_create_ticket:
            with unittest.mock.patch.object(
                threads, "check_can_dm_user", return_value=False
            ) as mock_check_can_dm_user:
                await cog.contact(cog, ctx, user)

        assert 1 == mock_create_ticket.call_count
        assert 1 == mock_check_can_dm_user.call_count
        assert 1 == ticket.thread.send.call_count

        mock_create_ticket.assert_called_once_with(
            ctx.message,
            recipient=user,
            raise_for_preexisting=True,
            send_initial_message=False,
            description="",
            creator=ctx.message.author,
        )
        # check for important words to be in the reply when user cannot be dmed
        sent_text = ticket.thread.send.call_args[0][0]
        important_words = ["not able to", "DM", user.name, user.discriminator]
        for word in important_words:
            assert str(word) in sent_text


class TestRelayMessageToUser:
    """
    Relay a message from guild to user and save it to the ticket.

    This should:
    - send message in thread
    - send message to user
    - error if the user cannot be dmed (TODO)
    - handle all of the following:
        - message content
        - message stickers
        - message attachments
    """

    ...

    @staticmethod
    @pytest.fixture
    def message():
        """Mock Message."""
        return mocks.MockMessage()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(["contents", "should_delete"], [["...", True]])
    async def test_reply_to_user_general(
        self,
        cog: threads.TicketsCog,
        ticket: threads.Ticket,
        message: typing.Union[discord.Message, mocks.MockMessage],
        contents: str,
        should_delete: bool,
    ):
        """Test the reply to user method does indeed send a message to the user."""
        message.author.colour = 5
        message.created_at = arrow.get(discord.utils.snowflake_time(message.created_at).timestamp()).datetime

        import modmail.utils.embeds

        modmail.utils.embeds.patch_embed()
        await cog.relay_message_to_user(ticket, message, contents, delete=should_delete)

        assert 1 == ticket.recipient.send.call_count
        ticket.recipient.send.assert_called_once()
        ticket.recipient.send.assert_awaited_once()


class TestRelayMessageToGuild:
    """
    Relay a message from guild to user and save it to the ticket.

    This should:
    - send message in thread
    - react to the user's message with a confirmation emoji that the above was successful
    - handle all of the following:
        - message content
        - message stickers
        - message attachments
    """

    ...


class TestReplyCommand:
    """
    Test reply command.

    Reply command needs to
    - respond to the user with errors
    - call the relay message to user method
    """

    ...


# class TestEditCommand:
#     ...
# class TestDeleteCommand:
#     ...
# class TestOnMessage:
#     ...
# class TestOnMessageEdit:
#     ...
# class TestOnMessageDelete:
#     ...
# class TestOnTyping:
#     ...
