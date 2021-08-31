from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from discord import InteractionType

from modmail.utils.cogs import ModmailCog

if TYPE_CHECKING:
    from discord import Interaction

    from modmail.bot import ModmailBot
    from modmail.log import ModmailLogger

logger: ModmailLogger = logging.getLogger(__name__)


class PaginatorCleaner(ModmailCog):
    """Handles paginators that were still active when the bot shut down."""

    def __init__(self, bot: ModmailBot):
        self.bot = bot

    @ModmailCog.listener()
    async def on_interaction(self, interaction: Interaction) -> None:
        """
        Remove components from paginator messages if they fail.

        The paginator handles all interactions while it is active, but if the bot is restarted,
        those interactions stop being dealt with.

        This handles all paginator interactions that fail, which should only happen if
        the paginator was unable to delete its message.
        """
        # paginator only has component interactions
        if not interaction.type == InteractionType.component:
            return
        logger.debug(f"Interaction sent by {interaction.user}.")
        logger.trace(f"Interaction data: {interaction.data}")
        if (
            interaction.data["custom_id"].startswith("pag_")
            and interaction.message.author.id == self.bot.user.id
        ):
            # sleep for two seconds to give the paginator time to respond.
            # this is due to discord requiring a response within 3 seconds,
            # and we don't want to let the paginator fail.
            await asyncio.sleep(2)
            if not interaction.response.is_done():
                await interaction.response.send_message(content="This paginator has expired.", ephemeral=True)
                await asyncio.sleep(0.1)  # sleep for 1 second so it isn't immediately removed
                await interaction.message.edit(view=None)


def setup(bot: ModmailBot) -> None:
    """Add the paginator cleaner to the bot."""
    bot.add_cog(PaginatorCleaner(bot))
