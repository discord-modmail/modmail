from modmail.bot import ModmailBot
from modmail.log import ModmailLogger
from modmail.utils.cogs import BotModes, ExtMetadata, ModmailCog


__all__ = ["PluginCog", ModmailBot, ModmailLogger, BotModes, ExtMetadata]


class PluginCog(ModmailCog):
    """
    The base class that all cogs must inherit from.

    A cog is a collection of commands, listeners, and optional state to
    help group commands together. More information on them can be found on
    the :ref:`ext_commands_cogs` page.

    When inheriting from this class, the options shown in :class:`CogMeta`
    are equally valid here.
    """

    pass
