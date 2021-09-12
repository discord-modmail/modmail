"""
Helper methods for responses from the bot to the user.

These help ensure consistency between errors, as they will all be consistent between different uses.
"""
import logging
from random import choice
from typing import List

import discord

from modmail.log import ModmailLogger


__all__ = (
    "default_success_color",
    "success_headers",
    "default_error_color",
    "error_headers",
    "send_positive_response",
    "send_negatory_response",
    "send_response",
)

_UNSET = object()

logger: ModmailLogger = logging.getLogger(__name__)


default_success_color = discord.Colour.green()
success_headers: List[str] = [
    "You got it.",
    "Done.",
    "Affirmative.",
    "As you wish.",
    "Okay.",
    "Fine by me.",
    "There we go.",
    "Sure!",
    "Your wish is my command.",
]

default_error_color = discord.Colour.red()
error_headers: List[str] = [
    "Abort!",
    "FAIL.",
    "I cannot do that.",
    "I'm leaving you.",
    "Its not me, its you.",
    "Hold up!",
    "Mistakes were made.",
    "Nope.",
    "Not happening.",
    "Oops.",
    "Something went wrong.",
    "Sorry, no.",
    "This will never work.",
    "Uh. No.",
    "\U0001f914",
    "That is not happening.",
    "Whups.",
]


async def send_positive_response(
    channel: discord.abc.Messageable,
    response: str,
    embed: discord.Embed = _UNSET,
    colour: discord.Colour = _UNSET,
    message: discord.Message = None,
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
    kwargs["allowed_mentions"] = kwargs.get("allowed_mentions", discord.AllowedMentions.none())

    logger.debug(f"Requested to send affirmative message to {channel!s}. Response: {response!s}")

    if embed is None:
        if message is None:
            return await channel.send(response, **kwargs)
        else:
            return await message.edit(response, **kwargs)

    if colour is _UNSET:
        colour = default_success_color

    if embed is _UNSET:
        embed = discord.Embed(colour=colour)
    embed.title = choice(success_headers)
    embed.description = response

    if message is None:
        return await channel.send(embed=embed, **kwargs)
    else:
        return await message.edit(embed=embed, **kwargs)


async def send_negatory_response(
    channel: discord.abc.Messageable,
    response: str,
    embed: discord.Embed = _UNSET,
    colour: discord.Colour = _UNSET,
    message: discord.Message = None,
    **kwargs,
) -> discord.Message:
    """
    Send a negatory response.

    Requires a messageable, and a response.
    If embed is set to None, this will send response as a plaintext message, with no allowed_mentions.
    If embed is provided, this method will send a response using the provided embed, edited in place.
    Extra kwargs are passed to Messageable.send()
    """
    kwargs["allowed_mentions"] = kwargs.get("allowed_mentions", discord.AllowedMentions.none())

    logger.debug(f"Requested to send affirmative message to {channel!s}. Response: {response!s}")

    if embed is None:
        if message is None:
            return await channel.send(response, **kwargs)
        else:
            return await message.edit(response, **kwargs)

    if colour is _UNSET:
        colour = default_error_color

    if embed is _UNSET:
        embed = discord.Embed(colour=colour)
    embed.title = choice(error_headers)
    embed.description = response

    if message is None:
        return await channel.send(embed=embed, **kwargs)
    else:
        return await message.edit(embed=embed, **kwargs)


async def send_response(
    channel: discord.abc.Messageable,
    response: str,
    success: bool,
    embed: discord.Embed = _UNSET,
    colour: discord.Colour = _UNSET,
    message: discord.Message = None,
    **kwargs,
) -> discord.Message:
    """
    Send a response based on success or failure.

    Requires a messageable, and a response.
    If embed is set to None, this will send response as a plaintext message, with no allowed_mentions.
    If embed is provided, this method will send a response using the provided embed, edited in place.
    Extra kwargs are passed to Messageable.send()
    """
    if success:
        return await send_positive_response(channel, response, embed, colour, message, **kwargs)
    else:
        return await send_negatory_response(channel, response, embed, colour, message, **kwargs)
