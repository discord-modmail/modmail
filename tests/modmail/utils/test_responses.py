import typing
import unittest.mock

import discord
import pytest

from modmail.utils import responses
from tests import mocks


@pytest.fixture
async def mock_channel() -> mocks.MockTextChannel:
    """Fixture for a channel."""
    return mocks.MockTextChannel()


@pytest.fixture
async def mock_message() -> mocks.MockMessage:
    """Fixture for a message."""
    return mocks.MockMessage()


@pytest.mark.asyncio
async def test_general_response_embed(mock_channel: mocks.MockTextChannel) -> None:
    """Test the positive response embed is correct when sending a new message."""
    content = "success!"
    _ = await responses.send_general_response(mock_channel, content)

    assert len(mock_channel.send.mock_calls) == 1

    _, _, called_kwargs = mock_channel.send.mock_calls[0]
    sent_embed: discord.Embed = called_kwargs["embed"]

    assert content == sent_embed.description


@pytest.mark.asyncio
async def test_no_embed(mock_channel: mocks.MockTextChannel):
    """Test general response without an embed."""
    content = "Look ma, no embed!"
    _ = await responses.send_general_response(mock_channel, content, embed=None)

    assert len(mock_channel.send.mock_calls) == 1

    _, called_args, _ = mock_channel.send.mock_calls[0]
    assert content == called_args[0]


@pytest.mark.asyncio
async def test_no_embed_edit(mock_message: mocks.MockMessage):
    """Test general response without an embed."""
    content = "Look ma, no embed!"
    _ = await responses.send_general_response(None, content, embed=None, message=mock_message)

    assert len(mock_message.edit.mock_calls) == 1

    _, called_args, _ = mock_message.edit.mock_calls[0]
    assert content == called_args[0]


@pytest.mark.asyncio
async def test_general_response_embed_edit(mock_message: mocks.MockMessage) -> None:
    """Test the positive response embed is correct when editing a message."""
    content = "hello, the code worked I guess!"
    _ = await responses.send_general_response(None, content, message=mock_message)

    assert len(mock_message.edit.mock_calls) == 1

    _, _, called_kwargs = mock_message.edit.mock_calls[0]
    sent_embed: discord.Embed = called_kwargs["embed"]

    assert content == sent_embed.description


def test_colour_aliases():
    """Test colour aliases are the same."""
    assert responses.DEFAULT_FAILURE_COLOR == responses.DEFAULT_FAILURE_COLOUR
    assert responses.DEFAULT_SUCCESS_COLOR == responses.DEFAULT_SUCCESS_COLOUR


@pytest.mark.parametrize(
    ["coro", "color", "title_list"],
    [
        [responses.send_positive_response, responses.DEFAULT_SUCCESS_COLOUR.value, responses.SUCCESS_HEADERS],
        [responses.send_negatory_response, responses.DEFAULT_FAILURE_COLOUR.value, responses.FAILURE_HEADERS],
    ],
)
@pytest.mark.asyncio
async def test_special_responses(
    mock_channel: mocks.MockTextChannel, coro, color: int, title_list: typing.List
):
    """Test the positive and negatory response methods."""
    _: unittest.mock.AsyncMock = await coro(mock_channel, "")

    assert len(mock_channel.send.mock_calls) == 1

    _, _, kwargs = mock_channel.send.mock_calls[0]
    embed_dict: dict = kwargs["embed"].to_dict()

    assert color == embed_dict.get("color")
    assert embed_dict.get("title") in title_list
