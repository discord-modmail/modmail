from dataclasses import dataclass
from enum import IntEnum, auto

from discord.ext import commands

from modmail.config import CONFIG


__all__ = (
    "BitwiseAutoEnum",
    "BotModeEnum",
    "ExtMetadata",
    "BOT_MODE",
    "ModmailCog",
)


class BitwiseAutoEnum(IntEnum):
    """Enum class which generates binary value for each item."""

    def _generate_next_value_(name, start, count, last_values) -> int:  # noqa: ANN001 N805
        """Override default enum auto() counter to return increasing powers of 2, 4, 8..."""
        return 1 << count


class BotModeEnum(BitwiseAutoEnum):
    """
    Valid modes for the bot.

    These values affect logging levels, which extensions are loaded, and so forth.
    """

    PRODUCTION = auto()
    DEVELOP = auto()
    PLUGIN_DEV = auto()


@dataclass()
class ExtMetadata:
    """Ext metadata class to determine if extension should load at runtime depending on bot configuration."""

    load_if_mode: BotModeEnum = BotModeEnum.PRODUCTION
    # this is to determine if the cog is allowed to be unloaded.
    no_unload: bool = False

    def __init__(self, *, load_if_mode: BotModeEnum = BotModeEnum.PRODUCTION, no_unload: bool = False):
        self.load_if_mode = load_if_mode
        self.no_unload = no_unload


def determine_bot_mode() -> int:
    """
    Figure out the bot mode from the configuration system.

    The configuration system uses true/false values, so we need to turn them into an integer for bitwise.
    """
    bot_mode = 0
    for mode in BotModeEnum:
        if getattr(CONFIG.dev.mode, str(mode).rsplit(".", maxsplit=1)[-1].lower(), True):
            bot_mode += mode.value
    return bot_mode


BOT_MODE = determine_bot_mode()


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
