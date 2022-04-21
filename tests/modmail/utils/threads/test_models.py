import enum
import typing
from functools import cached_property
from tokenize import maybe

import discord
import pytest

import modmail
from modmail.utils.threads import models
from tests import mocks


class TestMessageDict:
    """
    Custom message dictionary needs to store everything as a key and value.

    However, the keys are the ids of the passed values, and support
    getting either a corresponding key or message.
    """

    @pytest.fixture(scope="class")
    def messages(self):
        """
        Return a list of tuples of generated messages.

        The first msg in each tuple has a guild, while the second does not.
        The guild is the same mock accross all of the messages.
        """
        messages = []
        guild = mocks.MockGuild()
        for _ in range(7):
            messages.append([mocks.MockMessage(guild=guild), mocks.MockMessage(guild=None)])
        return messages

    def test_setitem(self, messages) -> models.MessageDict:
        """__setitem__ should set both the key and the value."""
        msg_dict = models.MessageDict()

        for m1, m2 in messages:
            msg_dict[m1] = m2

        # multiplying by 2 here because messages is a list of tuples
        assert len(messages) * 2 == len(msg_dict.keys())

        for m1, m2 in messages:
            assert m1.id in msg_dict.keys()
            assert m2.id in msg_dict.keys()
            assert m1 in msg_dict.values()
            assert m2 in msg_dict.values()

        # for daisy chaining the tests
        return msg_dict

    def test_getitem(self, messages):
        """__getitem__ should support being able to take either messages or ints as keys."""
        msg_dict = self.test_setitem(messages)
        for m1, m2 in messages:
            assert m2 == msg_dict[m1]
            assert m1 == msg_dict[m2]

        for m1, m2 in messages:
            assert m2 == msg_dict[m1.id]
            assert m1 == msg_dict[m2.id]

    def test_delitem(self, messages):
        """__delitem__ should delete both the key and the matching value."""
        msg_dict = self.test_setitem(messages)
        for m1, m2 in messages:

            del msg_dict[m1]
            assert m1 not in msg_dict.values()
            assert m2.id not in msg_dict.keys()
            assert m2 not in msg_dict.values()

    invalid_messages = [
        -1,
        "discord.Message",
        806247348703068210,
        mocks.MockTextChannel(),
        mocks.MockDMChannel(),
    ]

    @pytest.mark.parametrize("n1", invalid_messages)
    @pytest.mark.parametrize("n2", invalid_messages)
    def test_discord_message_required(self, n1, n2):
        """Test that MessageDict only takes messages as keys and values in assignment."""
        msg_dict = models.MessageDict()
        with pytest.raises(ValueError, match=r"discord\.Message"):
            msg_dict[n1] = n2


class TestTicket:
    """Tests for models.Ticket."""

    def test_ticket_attributes(self):
        """Tickets should have these attributes as part of their public api with the proper objects."""
        user = mocks.MockUser()
        thread = mocks.MockThread()
        message = mocks.MockMessage(id=thread.id)
        ticket = models.Ticket(user, thread, log_message=message)

        assert user == ticket.recipient
        assert thread == ticket.thread
        assert message == ticket.log_message
        assert isinstance(ticket.messages, models.MessageDict)
