from dataclasses import dataclass
from enum import IntEnum


class BotModes(IntEnum):
    """
    Valid modes for the bot.

    These values affect logging levels, which logs are loaded, and so forth.
    """

    production = int("1", 2)
    develop = int("10", 2)
    plugin_dev = int("100", 2)


BOT_MODES = BotModes


@dataclass()
class CogMetadata:
    """Cog metadata class to determine if cog should load at runtime depending on bot configuration."""

    # load if bot is in development mode
    # development mode is when the bot has its metacogs loaded, like the eval and extension cogs
    production: bool = False
    develop: bool = False
    # plugin development mode
    # used for loading bot plugins that help with plugin debugging
    plugin_dev: bool = False


def calc_mode(metadata: CogMetadata) -> int:
    """Calculate the combination of different variables and return the binary combination."""
    mode = int(getattr(metadata, "production", False))
    mode = mode + int(getattr(metadata, "develop", False) << 1) or 0
    mode = mode + (int(getattr(metadata, "plugin_dev", False)) << 2)
    return mode
