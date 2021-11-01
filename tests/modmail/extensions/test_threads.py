"""
Test Ticket extension.

To be written.
"""
import random
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
    thread = mocks.MockThread(guild=guild, parent=channel)
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
        received_ticket = cog.get_ticket(ticket.thread.id)
        assert ticket is received_ticket
        del received_ticket

        received_ticket = cog.get_ticket(ticket.recipient.id)
        assert ticket is received_ticket

    def test_invalid_get_ticket(self, cog: threads.TicketsCog, ticket_dict: dict):
        """Test invalid get_ticket ids raise a ThreadNotFoundError."""
        cog.bot._tickets = ticket_dict

        with pytest.raises(threads.ThreadNotFoundError):
            cog.get_ticket(mocks.generate_realistic_id())

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


# class TestReplyCommand:
#     ...
# class TestEditCommand:
#     ...
# class TestDeleteCommand:
#     ...
# class TestContactCommand:
#     ...
# class TestOnMessage:
#     ...
# class TestOnMessageEdit:
#     ...
# class TestOnMessageDelete:
#     ...
# class TestOnTyping:
#     ...
