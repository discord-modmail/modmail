from dataclasses import dataclass
from enum import IntEnum, auto

from discord.ext import commands


class BitwiseAutoEnum(IntEnum):
    """Enum class which generates binary value for each item."""

    def _generate_next_value_(name, start, count, last_values) -> int:  # noqa: ANN001 N805
        return 1 << count


class BotModes(BitwiseAutoEnum):
    """
    Valid modes for the bot.

    These values affect logging levels, which extensions are loaded, and so forth.
    """

    PRODUCTION = auto()
    DEVELOP = auto()
    PLUGIN_DEV = auto()


BOT_MODES = BotModes


@dataclass()
class ExtMetadata:
    """Ext metadata class to determine if extension should load at runtime depending on bot configuration."""

    load_if_mode: int = BotModes.PRODUCTION
    # this is to determine if the cog is allowed to be unloaded.
    no_unload: bool = False

    def __init__(self, load_if_mode: int = BotModes.PRODUCTION, no_unload: bool = False) -> "ExtMetadata":
        self.load_if_mode = load_if_mode
        self.no_unload = no_unload


class ModmailCog(commands.Cog):
    """
    The base class that all cogs must inherit from.

    A cog is a collection of commands, listeners, and optional state to
    help group commands together. More information on them can be found on
    the :ref:`ext_commands_cogs` page.

    When inheriting from this class, the options shown in :class:`CogMeta`
    are equally valid here.
    """

    pass
