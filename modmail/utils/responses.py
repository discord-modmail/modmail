import logging
from random import choice
from typing import List, final

import discord

from modmail.log import ModmailLogger


__all__ = ("Response",)

_UNSET = object()

logger: ModmailLogger = logging.getLogger()


@final
class Response:
    """Responses from the bot to the user."""

    success_color = discord.Colour.green()
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
    error_color = discord.Colour.red()
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

    @classmethod
    async def send_positive(
        cls,
        channel: discord.abc.Messageable,
        response: str,
        embed: discord.Embed = _UNSET,
        colour: discord.Colour = _UNSET,
        **kwargs,
    ) -> discord.Message:
        """
        Send an affirmative response.

        Requires a messageable, and a response.
        If embed is set to None, this will send response as a plaintext message, with no allowed_mentions.
        If embed is provided, this method will send a response using the provided embed, edited in place.
        Extra kwargs are passed to Messageable.send()
        """
        kwargs["allowed_mentions"] = kwargs.get("allowed_mentions", discord.AllowedMentions.none())

        logger.debug(f"Requested to send affirmative message to {channel!s}. Response: {response!s}")

        if embed is None:
            return await channel.send(response, **kwargs)

        if colour is _UNSET:
            colour = cls.success_color

        if embed is _UNSET:
            embed = discord.Embed(colour=colour)
        embed.title = choice(cls.success_headers)
        embed.description = response

        return await channel.send(embed=embed, **kwargs)

    @classmethod
    async def send_negatory(
        cls,
        channel: discord.abc.Messageable,
        response: str,
        embed: discord.Embed = _UNSET,
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
        kwargs["allowed_mentions"] = kwargs.get("allowed_mentions", discord.AllowedMentions.none())

        logger.debug(f"Requested to send affirmative message to {channel!s}. Response: {response!s}")

        if embed is None:
            return await channel.send(response, **kwargs)

        if colour is _UNSET:
            colour = cls.error_color

        if embed is _UNSET:
            embed = discord.Embed(colour=colour)
        embed.title = choice(cls.error_headers)
        embed.description = response

        return await channel.send(embed=embed, **kwargs)

    @classmethod
    async def send_response(
        cls,
        channel: discord.abc.Messageable,
        response: str,
        success: bool,
        embed: discord.Embed = _UNSET,
        colour: discord.Colour = _UNSET,
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
            return await cls.send_positive(channel, response, embed, colour, **kwargs)
        else:
            return await cls.send_negatory(channel, response, embed, colour, **kwargs)
