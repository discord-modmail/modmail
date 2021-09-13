from __future__ import annotations

from modmail.bot import ModmailBot
from modmail.log import ModmailLogger
from modmail.utils.cogs import BOT_MODE, BotModeEnum, ExtMetadata
from modmail.utils.cogs import ModmailCog as _ModmailCog


__all__ = [
    "PluginCog",
    BOT_MODE,
    BotModeEnum,
    ExtMetadata,
    ModmailBot,
    ModmailLogger,
]


class PluginCog(_ModmailCog):
    """
    The base class that all Plugin cogs must inherit from.

    A cog is a collection of commands, listeners, and optional state to
    help group commands together. More information on them can be found on
    the :ref:`ext_commands_cogs` page.

    When inheriting from this class, the options shown in :class:`CogMeta`
    are equally valid here.
    """

    pass
