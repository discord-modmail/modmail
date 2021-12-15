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
# NOTE: the characters are similar to what is printed, but not exact. This is to limit encoding issues.
JUMP_FIRST_LABEL = " \u276e\u276e "  # <<
BACK_LABEL = "  \u276e  "  # <
FORWARD_LABEL = "  \u276f  "  # >
JUMP_LAST_LABEL = " \u276f\u276f "  # >>
STOP_PAGINATE_EMOJI = "\u274c"  # [:x:] This is an emoji, which is treated differently from the above

NO_EMBED_FOOTER_BUMP = 15

_AUTOGENERATE = object()


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
        contents: Union[List[str], str],
        /,
        source_message: Optional[discord.Message] = None,
        embed: Union[Embed, bool, None] = _AUTOGENERATE,
        timeout: float = 180,
        *,
        footer_text: str = None,
        prefix: str = "```",
        suffix: str = "```",
        max_size: int = 2000,
        title: str = None,
        linesep: str = "\n",
        only_users: Optional[List[Union[discord.Object, discord.abc.User]]] = None,
        only_roles: Optional[List[Union[discord.Object, discord.Role]]] = None,
    ) -> None:
        """
        Creates a new Paginator instance.

        If source_message or only_users/only_roles are not provided, the paginator will respond to all users.
        If source message is provided and only_users is NOT provided, the paginator will respond
            to the author of the source message. To override this, pass an empty list to `only_users`.

        By default, an embed is created. However, a custom embed can
        be passed, or None can be passed to not use an embed.
        """
        self.index = 0
        self._pages: List[str] = []
        self.prefix = prefix
        self.suffix = suffix
        self.max_size = max_size
        self.linesep = linesep
        if embed is _AUTOGENERATE or embed is True:
            self.embed = Embed()
        else:
            if embed is False:
                embed = None
            self.embed = embed

        # used if embed is None
        self.content = ""
        if self.embed is None:
            self.title = title
            # need to set the max_size down a few to be able to set a "footer"
            # page indicator is "page xx of xx"
            self.max_size -= NO_EMBED_FOOTER_BUMP + len(self.title or "")
            if self.title is not None:
                self.max_size -= len(title)
            if footer_text is not None:
                self.max_size -= len(footer_text) + 1

        # temporary to support strings as contents. This will be changed when we added wrapping.
        if isinstance(contents, str):
            contents = [contents]

        # ensure that only_users are all users
        if only_users is not None:
            if isinstance(only_users, list):
                if not all(isinstance(user, (discord.Object, discord.abc.User)) for user in only_users):
                    raise InvalidArgumentError(
                        "only_users must be a list of discord.Object or discord.abc.User objects."
                    )
        elif source_message is not None:
            logger.debug("Only users not provided, using source message author.")
            only_users = [source_message.author]

        if only_roles is not None:
            if isinstance(only_roles, list):
                if not all(isinstance(role, (discord.Object, discord.Role)) for role in only_roles):
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
        if self.embed is not None:
            if not isinstance(self.embed.footer, EmbedProxy) and footer_text is None:
                footer_text = embed.footer
        self.footer_text = footer_text
        self.clear()
        for line in contents:
            self.add_line(line)
        self.close_page()
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
        embed: Embed = _AUTOGENERATE,
        *,
        footer_text: str = None,
        only: Optional[discord.abc.User] = None,
        channel: discord.abc.Messageable = None,
        show_jump_buttons_min_pages: int = 3,
        prefix: str = "",
        suffix: str = "",
        max_size: int = 4000,
        title: str = None,
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
            title=title,
            linesep=linesep,
            only_users=only_users,
            only_roles=only_roles,
        )

        if channel is None and source_message is None:
            raise MissingAttributeError("Both channel and source_message are None.")
        elif channel is None:
            channel = source_message.channel

        paginator.update_states()
        # if there's only one page, don't send the view
        if len(paginator.pages) < 2:
            if paginator.embed:
                await channel.send(embeds=[paginator.embed])
            else:
                await channel.send(content=paginator.content)

            return

        if len(paginator.pages) < (show_jump_buttons_min_pages or 3):
            for item in paginator.children:
                if getattr(item, "custom_id", None) in ["pag_jump_first", "pag_jump_last"]:
                    paginator.remove_item(item)

        if paginator.embed is None:
            msg: discord.Message = await channel.send(content=paginator.content, view=paginator)
        else:
            msg: discord.Message = await channel.send(embeds=[paginator.embed], view=paginator)

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
            if any(role.id in user_roles for role in self.only_roles):
                logger.debug("User is in allowed roles")
                return True
        await interaction.response.send_message(
            content="You are not authorised to use this paginator.", ephemeral=True
        )
        return False

    def update_states(self) -> None:
        """
        Disable specific components depending on paginator page and length.

        If the paginator has less than two pages, the jump buttons will be disabled.
        If the paginator is on the first page, the jump first/move back buttons will be disabled.
        if the paginator is on the last page, the jump last/move forward buttons will be disabled.
        """
        # update the footer
        page_indicator = f"Page {self.index+1}/{len(self._pages)}"
        if self.footer_text:
            footer_text = f"{self.footer_text} ({page_indicator})"
        else:
            footer_text = page_indicator

        if self.embed is None:
            self.content = (self.title or "") + "\n"
            self.content += self._pages[self.index]
            self.content += "\n" + footer_text

        else:
            self.embed.description = self._pages[self.index]
            self.embed.set_footer(text=footer_text)

        # determine if the jump buttons should be enabled
        more_than_two_pages = len(self._pages) > 2
        components = {
            "pag_jump_first": more_than_two_pages,
            "pag_prev": True,
            "pag_next": True,
            "pag_jump_last": more_than_two_pages,
        }

        if self.index == 0:
            # on the first page, disable buttons that would go to this page.
            logger.trace("Paginator is on the first page, disabling jump to first and previous buttons.")
            components["pag_jump_first"] = False
            components["pag_prev"] = False

        elif self.index == len(self._pages) - 1:
            # on the last page, disable buttons that would go to this page.
            logger.trace("Paginator is on the last page, disabling jump to last and next buttons.")
            components["pag_next"] = False
            components["pag_jump_last"] = False

        for child in self.children:
            # since its possible custom_id and disabled are not an attribute
            # we need to get them with getattr
            if getattr(child, "custom_id", None) in components.keys():
                if getattr(child, "disabled", None) is not None:
                    child.disabled = not components[child.custom_id]

    async def send_page(self, interaction: Interaction) -> None:
        """Send new page to discord, after updating the view to have properly disabled buttons."""
        self.update_states()

        if self.embed:
            await interaction.message.edit(embed=self.embed, view=self)
        else:
            await interaction.message.edit(content=self.content, view=self)

    @ui.button(label=JUMP_FIRST_LABEL, custom_id="pag_jump_first", style=ButtonStyle.primary)
    async def go_first(self, _: Button, interaction: Interaction) -> None:
        """Move the paginator to the first page."""
        self.index = 0
        await self.send_page(interaction)

    @ui.button(label=BACK_LABEL, custom_id="pag_prev", style=ButtonStyle.primary)
    async def go_previous(self, _: Button, interaction: Interaction) -> None:
        """Move the paginator to the previous page."""
        self.index -= 1
        await self.send_page(interaction)

    @ui.button(label=FORWARD_LABEL, custom_id="pag_next", style=ButtonStyle.primary)
    async def go_next(self, _: Button, interaction: Interaction) -> None:
        """Move the paginator to the next page."""
        self.index += 1
        await self.send_page(interaction)

    @ui.button(label=JUMP_LAST_LABEL, custom_id="pag_jump_last", style=ButtonStyle.primary)
    async def go_last(self, _: Button, interaction: Interaction) -> None:
        """Move the paginator to the last page."""
        self.index = len(self._pages) - 1
        await self.send_page(interaction)

    # NOTE: This method cannot be named `stop`, due to inheriting the method named stop from ui.View
    @ui.button(emoji=STOP_PAGINATE_EMOJI, custom_id="pag_stop_paginate", style=ButtonStyle.grey)
    async def _stop(self, _: Button, interaction: Interaction) -> None:
        """Stop the paginator early."""
        await interaction.response.defer()
        self.stop()
