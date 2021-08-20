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
from typing import Any, Dict, List, Optional, Union

import discord
from discord import ButtonStyle, Interaction
from discord.ui import Button, View, button

from modmail.log import ModmailLogger

# Stop button
STOP_PAGINATE_EMOJI = "\u274c"  # [:x:]

# Labels
JUMP_FIRST_LABEL = "\u2590\u276e\u2012"  # bar, left arrow, ‒
BACK_LABEL = "  \u276e  "  # left arrow
FORWARD_LABEL = "  \u276f  "  # right arrow
JUMP_LAST_LABEL = "\u2012\u276f\u258c"  # ‒, right arrow, bar
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


class ButtonPaginator(View):
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
        message: discord.Message = None,
        contents: Optional[List[str]] = None,
        embeds: Optional[List[discord.Embed]] = None,
        timeout: float = 180,
        embed: discord.Embed = None,
        only: Optional[discord.abc.User] = None,
    ) -> None:
        """Creates a new Paginator instance. At least one of ctx or message must be supplied."""
        self.source_msg = message
        self.only = only
        self.index = 0
        self.pages: List[Union[discord.Embed, str]] = []

        if not isinstance(timeout, (int, float)):
            raise InvalidArgumentError("timeout must be a float")

        self.timeout = float(timeout)

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
        # create the super so the children attributes are set
        super().__init__()

        # store component states for disabling
        self.states: Dict[str, Dict[str, Any]] = dict()
        for child in self.children:
            attrs = child.to_component_dict()
            self.states[attrs["custom_id"]] = attrs

    @classmethod
    async def paginate(
        cls,
        message: discord.Message = None,
        contents: Optional[List[str]] = None,
        embeds: Optional[List[discord.Embed]] = None,
        timeout: float = 180,
        only: Optional[discord.abc.User] = None,
        channel: discord.abc.Messageable = None,
    ) -> None:
        """Something."""
        paginator = cls(message, contents, embeds, timeout, only)

        if channel is None and message is None:
            raise MissingAttributeError("Both channel and message are None.")
        elif channel is None:
            channel = message.channel

        paginator.modify_states()
        if paginator.type == Types.CONTENTS:
            msg: discord.Message = await channel.send(
                content=paginator.pages[paginator.index], view=paginator
            )
        else:
            msg: discord.Message = await channel.send(embeds=paginator.pages[paginator.index], view=paginator)

        await paginator.wait()
        await msg.edit(view=None)

    async def interaction_check(self, interaction: Interaction) -> bool:
        """Check if the interaction is by the author of the paginatior."""
        if self.source_msg is None:
            return True
        if not (is_valid := self.source_msg.author.id == interaction.user.id):
            await interaction.response.send_message(
                content="This is not your message to paginate!", ephemeral=True
            )
        return is_valid

    def modify_states(self) -> None:
        """Disable specific components depending on paginator page and length."""
        less_than_2_pages = len(self.pages) <= 2
        components = {
            "jump_first": less_than_2_pages,
            "back": False,
            "next": False,
            "jump_last": less_than_2_pages,
        }

        if self.index == 0:
            components["jump_first"] = True
            components["back"] = True

        if self.index == len(self.pages) - 1:
            components["next"] = True
            components["jump_last"] = True

        for child in self.children:
            if child.custom_id in components.keys():
                if getattr(child, "disabled", None) is not None:
                    child.disabled = components[child.custom_id]
                    if getattr(child, "style", None) is not None:
                        child.style = ButtonStyle.secondary if child.disabled else ButtonStyle.primary

    async def send_page(self, interaction: Interaction) -> None:
        """Send new page."""
        self.modify_states()
        if self.type == Types.CONTENTS:
            await interaction.message.edit(content=self.pages[self.index], view=self)
        else:
            await interaction.message.edit(embed=self.pages[self.index], view=self)

    @button(label=JUMP_FIRST_LABEL, custom_id="jump_first", style=ButtonStyle.primary)
    async def go_first(self, button: Button, interaction: Interaction) -> None:
        """Move the paginator to the first page."""
        if self.index == 0:
            return

        self.index = 0
        await self.send_page(interaction)

    @button(label=BACK_LABEL, custom_id="back", style=ButtonStyle.primary)
    async def go_previous(self, button: Button, interaction: Interaction) -> None:
        """Move the paginator to the previous page."""
        if self.index == 0:
            return

        self.index -= 1
        await self.send_page(interaction)

    @button(label=FORWARD_LABEL, custom_id="next", style=ButtonStyle.primary)
    async def go_next(self, button: Button, interaction: Interaction) -> None:
        """Move the paginator to the next page."""
        if self.index == len(self.pages) - 1:
            return

        self.index += 1
        await self.send_page(interaction)

    @button(label=JUMP_LAST_LABEL, custom_id="jump_last", style=ButtonStyle.primary)
    async def go_last(self, button: Button, interaction: Interaction) -> None:
        """Move the paginator to the last page."""
        if self.index == len(self.pages) - 1:
            return

        self.index = len(self.pages) - 1
        await self.send_page(interaction)

    @button(emoji=STOP_PAGINATE_EMOJI, custom_id="stop_paginate", style=ButtonStyle.grey)
    async def _stop(self, button: Button, interaction: Interaction) -> None:
        """Stop the paginator early."""
        await interaction.response.defer()
        self.stop()
