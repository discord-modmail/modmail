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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import discord
from discord import ButtonStyle
from discord.ext.commands import Paginator as DpyPaginator
from discord.ui import View, button

if TYPE_CHECKING:
    from discord import Interaction
    from discord.ui import Button

    from modmail.log import ModmailLogger


# Stop button
STOP_PAGINATE_EMOJI = "\u274c"  # [:x:]

# Labels
JUMP_FIRST_LABEL = "\u2590\u276e\u2012"  # bar, left arrow, ‒
BACK_LABEL = "  \u276e  "  # left arrow
FORWARD_LABEL = "  \u276f  "  # right arrow
JUMP_LAST_LABEL = "\u2012\u276f\u258c"  # ‒, right arrow, bar


logger: "ModmailLogger" = logging.getLogger(__name__)


class MissingAttributeError(Exception):
    """Missing attribute."""

    pass


class InvalidArgumentError(Exception):
    """Improper argument."""

    pass


class ButtonPaginator(View, DpyPaginator):
    """
    A class that helps in paginating long messages/embeds, which can be interacted via discord buttons.

    Attributes
    ----------
    ctx: commands.Context
        Context of the message.
    contents : List[str]
        List of contents.
    timeout : float, default 180
        A timeout of receiving Interactions.
    only : discord.abc.User, optional
        If a parameter is given, the paginator will respond only to the selected user.
    auto_delete : bool, default False
        Whether to delete message after timeout.
    """

    def __init__(
        self,
        contents: List[str],
        /,
        source_message: Optional[discord.Message] = None,
        embed: discord.Embed = None,
        timeout: float = 180,
        *,
        prefix: str = "```",
        suffix: str = "```",
        max_size: int = 2000,
        linesep: str = "\n",
        only_users: Optional[List[discord.abc.User]] = None,
    ) -> None:
        """Creates a new Paginator instance. At least one of ctx or message must be supplied."""
        self.only_users = only_users
        self._index = 0
        self._pages: List[Union[discord.Embed, str]] = []
        self.source_message = source_message
        self.prefix = prefix
        self.suffix = suffix
        self.max_size = max_size
        self.linesep = linesep
        self._embed = embed

        if not isinstance(timeout, (int, float)):
            raise InvalidArgumentError("timeout must be a float")

        self.timeout = float(timeout)
        self.clear()
        for line in contents:
            self.add_line(line)

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
        contents: Optional[List[str]] = None,
        source_message: discord.Message = None,
        /,
        timeout: float = 180,
        embed: discord.Embed = None,
        *,
        only: Optional[discord.abc.User] = None,
        channel: discord.abc.Messageable = None,
        prefix: str = "",
        suffix: str = "",
        max_size: int = 4000,
        linesep: str = "\n",
        only_users: Optional[List[discord.abc.User]] = None,
    ) -> None:
        """Create a paginator, and paginate the provided lines."""
        paginator = cls(
            contents,
            source_message=source_message,
            timeout=timeout,
            embed=embed,
            prefix=prefix,
            suffix=suffix,
            max_size=max_size,
            linesep=linesep,
            only_users=only_users,
        )

        if channel is None and source_message is None:
            raise MissingAttributeError("Both channel and message are None.")
        elif channel is None:
            channel = source_message.channel

        paginator.modify_states()
        if len(paginator.pages) >= 2:
            msg: discord.Message = await channel.send(
                content=paginator.pages[paginator._index], view=paginator
            )
        else:
            await channel.send(content=paginator.pages[paginator._index])
            return

        await paginator.wait()
        await msg.edit(view=None)

    async def interaction_check(self, interaction: "Interaction") -> bool:
        """Check if the interaction is by the author of the paginatior."""
        if self.source_message is None:
            return True
        if not (is_valid := self.source_message.author.id == interaction.user.id):
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

        if self._index == 0:
            components["jump_first"] = True
            components["back"] = True

        if self._index == len(self.pages) - 1:
            components["next"] = True
            components["jump_last"] = True

        for child in self.children:
            if child.custom_id in components.keys():
                if getattr(child, "disabled", None) is not None:
                    child.disabled = components[child.custom_id]
                    if getattr(child, "style", None) is not None:
                        child.style = ButtonStyle.secondary if child.disabled else ButtonStyle.primary

    async def send_page(self, interaction: "Interaction") -> None:
        """Send new page."""
        self.modify_states()
        await interaction.message.edit(content=self.pages[self._index], view=self)

    @button(label=JUMP_FIRST_LABEL, custom_id="jump_first", style=ButtonStyle.primary)
    async def go_first(self, button: "Button", interaction: "Interaction") -> None:
        """Move the paginator to the first page."""
        if self._index == 0:
            return

        self._index = 0
        await self.send_page(interaction)

    @button(label=BACK_LABEL, custom_id="back", style=ButtonStyle.primary)
    async def go_previous(self, button: "Button", interaction: "Interaction") -> None:
        """Move the paginator to the previous page."""
        if self._index == 0:
            return

        self._index -= 1
        await self.send_page(interaction)

    @button(label=FORWARD_LABEL, custom_id="next", style=ButtonStyle.primary)
    async def go_next(self, button: "Button", interaction: "Interaction") -> None:
        """Move the paginator to the next page."""
        if self._index == len(self.pages) - 1:
            return

        self._index += 1
        await self.send_page(interaction)

    @button(label=JUMP_LAST_LABEL, custom_id="jump_last", style=ButtonStyle.primary)
    async def go_last(self, button: "Button", interaction: "Interaction") -> None:
        """Move the paginator to the last page."""
        if self._index == len(self.pages) - 1:
            return

        self._index = len(self.pages) - 1
        await self.send_page(interaction)

    @button(emoji=STOP_PAGINATE_EMOJI, custom_id="stop_paginate", style=ButtonStyle.grey)
    async def _stop(self, button: "Button", interaction: "Interaction") -> None:
        """Stop the paginator early."""
        await interaction.response.defer()
        self.stop()
