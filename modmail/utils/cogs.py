from dataclasses import dataclass
from enum import IntEnum, auto
from typing import TYPE_CHECKING

from discord.ext import commands


if TYPE_CHECKING:  # pragma: nocover
    import modmail.bot


class BitwiseAutoEnum(IntEnum):
    """Enum class which generates binary value for each item."""

    def _generate_next_value_(name, start, count, last_values) -> int:  # noqa: ANN001 N805
        """Override default enum auto() counter to return increasing powers of 2, 4, 8..."""
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

    def __init__(self, bot: "modmail.bot.ModmailBot"):
        self.dispatcher = bot.dispatcher
        self.dispatcher.activate(self)

    def cog_unload(self) -> None:
        """Ensure dispatched class methods are unloaded when the cog is unloaded."""
        self.dispatcher.deactivate(self)
