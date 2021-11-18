from __future__ import annotations

import logging

from modmail.addons.helpers import PluginCog
from modmail.bot import ModmailBot
from modmail.log import ModmailLogger


logger: ModmailLogger = logging.getLogger(__name__)


class WorkingPlugin(PluginCog):
    """Demonstration plugin for testing."""

    pass


def setup(bot: ModmailBot) -> None:
    """Add the gateway logger to the bot."""
    bot.add_cog(WorkingPlugin(bot))
