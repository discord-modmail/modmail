"""
Helper methods for responses from the bot to the user.

These help ensure consistency between errors, as they will all be consistent between different uses.
"""
import logging
import random
import typing

import discord
from discord.ext import commands

from modmail.log import ModmailLogger


__all__ = (
    "DEFAULT_SUCCESS_COLOUR",
    "DEFAULT_SUCCESS_COLOR",
    "SUCCESS_HEADERS",
    "DEFAULT_FAILURE_COLOUR",
    "DEFAULT_FAILURE_COLOR",
    "FAILURE_HEADERS",
    "send_general_response",
    "send_positive_response",
    "send_negatory_response",
)

_UNSET = object()

logger: ModmailLogger = logging.getLogger(__name__)


DEFAULT_SUCCESS_COLOUR = discord.Colour.green()
DEFAULT_SUCCESS_COLOR = DEFAULT_SUCCESS_COLOUR
SUCCESS_HEADERS: typing.List[str] = [
    "Affirmative",
    "As you wish",
    "Done",
    "Fine by me",
    "There we go",
    "Sure!",
    "Okay",
    "You got it",
    "Your wish is my command",
]

DEFAULT_FAILURE_COLOUR = discord.Colour.red()
DEFAULT_FAILURE_COLOR = DEFAULT_FAILURE_COLOUR
FAILURE_HEADERS: typing.List[str] = [
    "Abort!",
    "I cannot do that",
    "Hold up!",
    "I was unable to interpret that",
    "Not understood",
    "Oops",
    "Something went wrong",
    "\U0001f914",
    "Unable to complete your command",
]


async def send_general_response(
    channel: discord.abc.Messageable,
    response: str,
    *,
    message: discord.Message = None,
    embed: discord.Embed = _UNSET,
    colour: discord.Colour = None,
    title: str = None,
    _kind: typing.Literal["general", "affirmative", "negatory"] = "general",
    **kwargs,
) -> discord.Message:
    """
    Helper method to send a response.

    Shortcuts are provided as `send_positive_response` and `send_negatory_response` which
    fill in the title and colour automatically.
    """
    kwargs["allowed_mentions"] = kwargs.get("allowed_mentions", discord.AllowedMentions.none())

    if isinstance(channel, commands.Context):  # pragma: nocover
        channel = channel.channel

    logger.debug(f"Requested to send {_kind} response message to {channel!s}. Response: {response!s}")

    if embed is None:
        if message is None:
            return await channel.send(response, **kwargs)
        else:
            return await message.edit(response, **kwargs)

    if embed is _UNSET:  # pragma: no branch
        embed = discord.Embed(colour=colour or discord.Embed.Empty)

    if title is not None:
        embed.title = title

    embed.description = response

    if message is None:
        return await channel.send(embed=embed, **kwargs)
    else:
        return await message.edit(embed=embed, **kwargs)


async def send_positive_response(
    channel: discord.abc.Messageable,
    response: str,
    *,
    colour: discord.Colour = _UNSET,
    **kwargs,
) -> discord.Message:
    """
    Send an affirmative response.

    Requires a messageable, and a response.
    If embed is set to None, this will send response as a plaintext message, with no allowed_mentions.
    If embed is provided, this method will send a response using the provided embed, edited in place.
    Extra kwargs are passed to Messageable.send()

    If message is provided, it will attempt to edit that message rather than sending a new one.
    """
    if colour is _UNSET:  # pragma: no branch
        colour = DEFAULT_SUCCESS_COLOUR

    kwargs["title"] = kwargs.get("title", random.choice(SUCCESS_HEADERS))

    return await send_general_response(
        channel=channel,
        response=response,
        colour=colour,
        _kind="affirmative",
        **kwargs,
    )


async def send_negatory_response(
    channel: discord.abc.Messageable,
    response: str,
    *,
    colour: discord.Colour = _UNSET,
    **kwargs,
) -> discord.Message:
    """
    Send a negatory response.

    Requires a messageable, and a response.
    If embed is set to None, this will send response as a plaintext message, with no allowed_mentions.
    If embed is provided, this method will send a response using the provided embed, edited in place.
    Extra kwargs are passed to Messageable.send()
    """
    if colour is _UNSET:  # pragma: no branch
        colour = DEFAULT_FAILURE_COLOUR

    kwargs["title"] = kwargs.get("title", random.choice(FAILURE_HEADERS))

    return await send_general_response(
        channel=channel,
        response=response,
        colour=colour,
        _kind="negatory",
        **kwargs,
    )
