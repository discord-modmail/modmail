# original source:
# https://github.com/python-discord/bot/blob/a8869b4d60512b173871c886321b261cbc4acca9/bot/utils/extensions.py
# MIT License 2021 Python Discord
import importlib
import inspect
import logging
import pkgutil
import typing as t

from modmail import extensions
from modmail.config import config
from modmail.log import ModmailLogger
from modmail.utils.cogs import BOT_MODES, BotModes, ExtMetadata


log: ModmailLogger = logging.getLogger(__name__)

EXT_METADATA = ExtMetadata


EXTENSIONS: t.Dict[str, t.Tuple[bool, bool]] = dict()
NO_UNLOAD: t.List[str] = list()


def unqualify(name: str) -> str:
    """Return an unqualified name given a qualified module/package `name`."""
    return name.rsplit(".", maxsplit=1)[-1]


def determine_bot_mode() -> int:
    """
    Figure out the bot mode from the configuration system.

    The configuration system uses true/false values, so we need to turn them into an integer for bitwise.
    """
    bot_mode = 0
    _config = config()
    for mode in BotModes:
        if getattr(_config.user.dev.mode, unqualify(str(mode)).lower(), True):
            bot_mode += mode.value
    return bot_mode


BOT_MODE = determine_bot_mode()


log.trace(f"BOT_MODE value: {BOT_MODE}")
log.debug(f"Dev mode status: {bool(BOT_MODE & BOT_MODES.DEVELOP)}")
log.debug(f"Plugin dev mode status: {bool(BOT_MODE & BOT_MODES.PLUGIN_DEV)}")


def walk_extensions() -> t.Iterator[t.Tuple[str, t.Tuple[bool, bool]]]:
    """Yield extension names from the modmail.exts subpackage."""

    def on_error(name: str) -> t.NoReturn:
        raise ImportError(name=name)  # pragma: no cover

    for module in pkgutil.walk_packages(extensions.__path__, f"{extensions.__name__}.", onerror=on_error):
        if unqualify(module.name).startswith("_"):
            # Ignore module/package names starting with an underscore.
            continue

        imported = importlib.import_module(module.name)
        if module.ispkg:
            if not inspect.isfunction(getattr(imported, "setup", None)):
                # If it lacks a setup function, it's not an extension.
                continue

        ext_metadata: ExtMetadata = getattr(imported, "EXT_METADATA", None)
        if ext_metadata is not None:
            # check if this cog is dev only or plugin dev only
            load_cog = bool(int(ext_metadata.load_if_mode) & BOT_MODE)
            log.trace(f"Load cog {module.name!r}?: {load_cog}")
            no_unload = ext_metadata.no_unload
            yield module.name, (load_cog, no_unload)
            continue

        log.notice(f"Cog {module.name!r} is missing an EXT_METADATA variable. Assuming its a normal cog.")

        # Presume Production Mode/Metadata defaults if metadata var does not exist.
        yield module.name, (ExtMetadata.load_if_mode, ExtMetadata.no_unload)
