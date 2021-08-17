"""
Paginator.

Adapated from: https://github.com/khk4912/EZPaginator/tree/84b5213741a78de266677b805c6f694ad94fedd6

MIT License

Copyright (c) 2020 khk4912

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


CHANGES:
- made this work with buttons instead of reactions
- comply with black and flake8
"""
import logging
from enum import Enum
from typing import List, Optional, Union

import discord
from discord import ButtonStyle, Interaction
from discord.ext import commands
from discord.ui import Button, View, button

from modmail.log import ModmailLogger

JUMP_FIRST_EMOJI = "\u23EE"  # [:track_previous:]
BACK_EMOJI = "\u2B05"  # [:arrow_left:]
FORWARD_EMOJI = "\u27A1"  # [:arrow_right:]
JUMP_LAST_EMOJI = "\u23ED"  # [:track_next:]
STOP_PAGINATE_EMOJI = "\U0001f6d1"  # [:octagonal_sign:]

logger: ModmailLogger = logging.getLogger(__name__)


class MissingAttributeError(Exception):
    """Missing attribute."""

    pass


class TooManyAttributesError(Exception):
    """Too many attributes."""

    pass


class InvalidArgumentError(Exception):
    """Improper argument."""

    pass


class Types(Enum):
    """Types of pagination."""

    CONTENTS = 0
    EMBEDS = 1


class Paginator(View):
    """
    Class for Pagination.

    Attributes
    ----------
    ctx: commands.Context
        Context of the message.
    contents : List[str], optional
        List of contents.
    embeds : List[Embed], optional
        List of embeds. If both contents and embeds are given, the priority is embed.
    timeout : float, default 180
        A timeout of receiving Interactions.
    only : discord.abc.User, optional
        If a parameter is given, the paginator will respond only to the selected user.
    basic_emojis : List[Emoji], optional
        Custom basic emoji list. There should be 2 emojis.
    extended_emojis : List[Emoji], optional
        Extended emoji list, There should be 4 emojis.
    auto_delete : bool, default False
        Whether to delete message after timeout.
    """

    def __init__(
        self,
        ctx: commands.Context = None,
        contents: Optional[List[str]] = None,
        embeds: Optional[List[discord.Embed]] = None,
        timeout: float = 180,
        embed: discord.Embed = None,
        only: Optional[discord.abc.User] = None,
    ) -> None:
        """Creates a new Paginator instance. At least one of ctx or message must be supplied."""
        self.ctx = ctx
        self.timeout = timeout
        self.only = only
        self.index = 0
        self.pages: List[Union[discord.Embed, str]] = []

        if not (isinstance(timeout, float) or isinstance(timeout, int)):
            raise InvalidArgumentError("timeout must be a float")

        if contents is None and embeds is None:
            raise MissingAttributeError("Both contents and embeds are None.")
        elif contents is not None and embeds is not None:
            raise TooManyAttributesError("Both contents and embeds are given. Please choose one.")
        if contents:
            # contents exist, so embeds is be None
            self.pages = contents
            self.type = Types.CONTENTS
        else:
            self.pages = embeds
            self.type = Types.EMBEDS

        super().__init__()

    @classmethod
    async def paginate(
        cls,
        ctx: commands.Context = None,
        contents: Optional[List[str]] = None,
        embeds: Optional[List[discord.Embed]] = None,
        timeout: float = 180,
        only: Optional[discord.abc.User] = None,
    ) -> None:
        """Something."""
        paginator = cls(ctx, contents, embeds, timeout, only)

        # remove buttons based on how many pages we have
        if len(paginator.pages) <= 2:
            pass
            # paginator.remove_item()
        paginator.modify_disabled()
        if paginator.type == Types.CONTENTS:
            msg: discord.Message = await ctx.send(content=paginator.pages[paginator.index], view=paginator)
        else:
            msg: discord.Message = await ctx.send(embeds=paginator.pages[paginator.index], view=paginator)

        await paginator.wait()
        await msg.edit(view=None)

    async def interaction_check(self, interaction: Interaction) -> bool:
        """Check if the interaction is by the author of the paginatior."""
        if not (is_valid := self.ctx.author.id == interaction.user.id):
            await interaction.response.send_message(
                content="This is not your message to paginate!", ephemeral=True
            )
        return is_valid

    def modify_disabled(self) -> None:
        """Disable specific buttons depending on paginator page and length."""
        ids = ["jump_first", "back", "next", "jump_last"]
        states = []
        if len(self.pages) > 2:
            states = [False for _ in range(4)]
        elif len(self.pages) == 2:
            # there are two pages
            states = [True, False, False, True]
        else:
            # there is only one page
            states = [True for _ in range(4)]
        if self.index == 0:
            for i in range(2):
                states[i] = True
        elif self.index == len(self.pages) - 1:
            for i in range(2):
                states[(-1 * (i + 1))] = True
        for item in self.children:
            id = item.to_component_dict()["custom_id"]
            if id in ids:
                item.disabled = states[ids.index(id)]

    async def send_page(self, interaction: Interaction) -> None:
        """Send new page."""
        self.modify_disabled()
        if self.type == Types.CONTENTS:
            await interaction.message.edit(content=self.pages[self.index], view=self)
        else:
            await interaction.message.edit(embed=self.pages[self.index], view=self)

    @button(emoji=JUMP_FIRST_EMOJI, custom_id="jump_first")
    async def go_first(self, button: Button, interaction: Interaction) -> None:
        """Move the paginator to the first page."""
        if self.index == 0:
            return

        self.index = 0
        await self.send_page(interaction)

    @button(emoji=BACK_EMOJI, custom_id="back")
    async def go_previous(self, button: Button, interaction: Interaction) -> None:
        """Move the paginator to the previous page."""
        if self.index == 0:
            button.disabled = True
            await interaction.message.edit(view=self)
            return

        self.index -= 1
        await self.send_page(interaction)

    @button(emoji=FORWARD_EMOJI, custom_id="next")
    async def go_next(self, button: Button, interaction: Interaction) -> None:
        """Move the paginator to the next page."""
        if self.index < len(self.pages) - 1:
            self.index += 1
            await self.send_page(interaction)

    @button(emoji=JUMP_LAST_EMOJI, custom_id="jump_last")
    async def go_last(self, button: Button, interaction: Interaction) -> None:
        """Move the paginator to the last page."""
        if self.index < len(self.pages) - 1:
            self.index = len(self.pages) - 1
            await self.send_page(interaction)

    @button(emoji=STOP_PAGINATE_EMOJI, style=ButtonStyle.grey, custom_id="stop_paginate")
    async def _stop(self, button: Button, interaction: Interaction) -> None:
        """Stop the paginator early."""
        await interaction.response.defer()
        self.stop()
