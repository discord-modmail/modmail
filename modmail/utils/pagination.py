"""
Paginator.

Originally adapated from: https://github.com/khk4912/EZPaginator/tree/84b5213741a78de266677b805c6f694ad94fedd6
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import discord
from discord import ButtonStyle, ui
from discord.embeds import Embed, EmbedProxy
from discord.ext.commands import Paginator as DpyPaginator

from modmail.utils.errors import InvalidArgumentError, MissingAttributeError

if TYPE_CHECKING:
    from discord import Interaction
    from discord.ui import Button

    from modmail.log import ModmailLogger


# Labels
# NOTE: the characters are similar to what is printed, but not exact.
JUMP_FIRST_LABEL = " \u276e\u276e "  # <<
BACK_LABEL = "  \u276e  "  # <
FORWARD_LABEL = "  \u276f  "  # >
JUMP_LAST_LABEL = " \u276f\u276f "  # >>
STOP_PAGINATE_EMOJI = "\u274c"  # [:x:] This is an emoji, which is treated differently from the above

logger: ModmailLogger = logging.getLogger(__name__)


class ButtonPaginator(ui.View, DpyPaginator):
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
        embed: Embed = None,
        timeout: float = 180,
        *,
        footer_text: str = None,
        prefix: str = "```",
        suffix: str = "```",
        max_size: int = 2000,
        linesep: str = "\n",
        only_users: Optional[List[Union[discord.Object, discord.abc.User]]] = None,
        only_roles: Optional[List[Union[discord.Object, discord.Role]]] = None,
    ) -> None:
        """
        Creates a new Paginator instance.

        If source_message or only_users/only_roles are not provided, the paginator will respond to all users.
        If source message is provided and only_users is NOT provided, the paginator will respond
            to the author of the source message. To override this, pass an empty list to `only_users`.

        """
        self._index = 0
        self._pages: List[str] = []
        self.prefix = prefix
        self.suffix = suffix
        self.max_size = max_size
        self.linesep = linesep
        self._embed = embed or Embed()

        # ensure that only_users are all users
        if only_users is not None:
            if isinstance(only_users, list):
                for user in only_users:
                    if not isinstance(user, (discord.Object, discord.abc.User)):
                        raise InvalidArgumentError(
                            "only_users must be a list of discord.Object or discord.abc.User objects."
                        )
        elif source_message is not None:
            logger.debug("Only users not provided, using source message author.")
            only_users = [source_message.author]

        if only_roles is not None:
            if isinstance(only_roles, list):
                for role in only_roles:
                    if not isinstance(role, (discord.Object, discord.Role)):
                        raise InvalidArgumentError(
                            "only_roles must be a list of discord.Object or discord.Role objects."
                        )

        self.only_users = only_users
        self.only_roles = only_roles

        if not isinstance(timeout, (int, float)):
            raise InvalidArgumentError("timeout must be a float")

        self.timeout = float(timeout)

        # set footer to embed.footer if embed is set
        # this is because we will be modifying the footer of this embed
        if embed is not None:
            if not isinstance(embed.footer, EmbedProxy) and footer_text is None:
                footer_text = embed.footer
        self.footer_text = footer_text
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
        embed: Embed = None,
        *,
        footer_text: str = None,
        only: Optional[discord.abc.User] = None,
        channel: discord.abc.Messageable = None,
        prefix: str = "",
        suffix: str = "",
        max_size: int = 4000,
        linesep: str = "\n",
        only_users: Optional[List[Union[discord.Object, discord.abc.User]]] = None,
        only_roles: Optional[List[Union[discord.Object, discord.abc.Role]]] = None,
    ) -> None:
        """
        Create a paginator, and paginate the provided lines.

        One of source message or channel is required.
        """
        paginator = cls(
            contents,
            source_message=source_message,
            timeout=timeout,
            embed=embed,
            footer_text=footer_text,
            prefix=prefix,
            suffix=suffix,
            max_size=max_size,
            linesep=linesep,
            only_users=only_users,
            only_roles=only_roles,
        )

        if channel is None and source_message is None:
            raise MissingAttributeError("Both channel and source_message are None.")
        elif channel is None:
            channel = source_message.channel

        paginator.modify_states()
        paginator._embed.description = paginator.pages[paginator._index]
        paginator._embed.set_footer(text=paginator.get_footer())
        # if there's only one page, don't send the view
        if len(paginator.pages) < 2:
            await channel.send(embeds=[paginator._embed])
            return
        else:
            msg: discord.Message = await channel.send(embeds=[paginator._embed], view=paginator)

        await paginator.wait()
        await msg.edit(view=None)

    async def interaction_check(self, interaction: Interaction) -> bool:
        """Check if the interaction is by the author of the paginator."""
        if self.only_users is not None:
            logger.trace(f"All allowed users: {self.only_users}")
            if any(user.id == interaction.user.id for user in self.only_users):
                logger.debug("User is in allowed users")
                return True
        if self.only_roles is not None:
            logger.trace(f"All allowed roles: {self.only_roles}")
            user_roles = [role.id for role in interaction.user.roles]
            for role in self.only_roles:
                if role.id in user_roles:
                    logger.debug("User is in allowed roles")
                    return True
        await interaction.response.send_message(
            content="You are not authorised to use this paginator.", ephemeral=True
        )
        return False

    def get_footer(self) -> str:
        """Returns the footer text."""
        self._embed.description = self._pages[self._index]
        page_indicator = f"Page {self._index+1}/{len(self._pages)}"
        footer_txt = (
            f"{self.footer_text} ({page_indicator})" if self.footer_text is not None else page_indicator
        )
        return footer_txt

    def modify_states(self) -> None:
        """
        Disable specific components depending on paginator page and length.

        If the paginatot has less than two pages, the jump buttons will be disabled.
        If the paginator is on the first page, the jump first/move back buttons will be disabled.
        if the paginator is on the last page, the jump last/move forward buttons will be disabled.
        """
        less_than_2_pages = len(self._pages) <= 2
        components = {
            "pag_jump_first": less_than_2_pages,
            "pag_back": False,
            "pag_next": False,
            "pag_jump_last": less_than_2_pages,
        }

        if self._index == 0:
            components["pag_jump_first"] = True
            components["pag_back"] = True

        if self._index == len(self._pages) - 1:
            components["pag_next"] = True
            components["pag_jump_last"] = True

        for child in self.children:
            if child.custom_id in components.keys():
                if getattr(child, "disabled", None) is not None:
                    child.disabled = components[child.custom_id]

    async def send_page(self, interaction: Interaction) -> None:
        """Send new page to discord, after updating the view to have properly disabled buttons."""
        self.modify_states()

        self._embed.set_footer(text=self.get_footer())
        await interaction.message.edit(embed=self._embed, view=self)

    @ui.button(label=JUMP_FIRST_LABEL, custom_id="pag_jump_first", style=ButtonStyle.primary)
    async def go_first(self, _: Button, interaction: Interaction) -> None:
        """Move the paginator to the first page."""
        self._index = 0
        await self.send_page(interaction)

    @ui.button(label=BACK_LABEL, custom_id="pag_back", style=ButtonStyle.primary)
    async def go_previous(self, _: Button, interaction: Interaction) -> None:
        """Move the paginator to the previous page."""
        self._index -= 1
        await self.send_page(interaction)

    @ui.button(label=FORWARD_LABEL, custom_id="pag_next", style=ButtonStyle.primary)
    async def go_next(self, _: Button, interaction: Interaction) -> None:
        """Move the paginator to the next page."""
        self._index += 1
        await self.send_page(interaction)

    @ui.button(label=JUMP_LAST_LABEL, custom_id="pag_jump_last", style=ButtonStyle.primary)
    async def go_last(self, _: Button, interaction: Interaction) -> None:
        """Move the paginator to the last page."""
        self._index = len(self._pages) - 1
        await self.send_page(interaction)

    # NOTE: This method cannot be named `stop`, due to inheriting the method named stop from ui.View
    @ui.button(emoji=STOP_PAGINATE_EMOJI, custom_id="pag_stop_paginate", style=ButtonStyle.grey)
    async def _stop(self, _: Button, interaction: Interaction) -> None:
        """Stop the paginator early."""
        await interaction.response.defer()
        self.stop()
