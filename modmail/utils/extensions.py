# original source:
# https://github.com/python-discord/bot/blob/a8869b4d60512b173871c886321b261cbc4acca9/bot/utils/extensions.py
# MIT License 2021 Python Discord
import importlib
import inspect
import logging
import pkgutil
from typing import Iterator, NoReturn

from modmail import exts
from modmail.config import CONFIG
from modmail.log import ModmailLogger
from modmail.utils.cogs import BOT_MODES, calc_mode

BOT_MODE = calc_mode(CONFIG.dev)
log: ModmailLogger = logging.getLogger(__name__)
log.trace(f"BOT_MODE value: {BOT_MODE}")
log.debug(f"Dev mode status: {bool(BOT_MODE & BOT_MODES.develop)}")
log.debug(f"Plugin dev mode status: {bool(BOT_MODE & BOT_MODES.plugin_dev)}")


def unqualify(name: str) -> str:
    """Return an unqualified name given a qualified module/package `name`."""
    return name.rsplit(".", maxsplit=1)[-1]


def walk_extensions() -> Iterator[str]:
    """Yield extension names from the modmail.exts subpackage."""

    def on_error(name: str) -> NoReturn:
        raise ImportError(name=name)  # pragma: no cover

    for module in pkgutil.walk_packages(exts.__path__, f"{exts.__name__}.", onerror=on_error):
        if unqualify(module.name).startswith("_"):
            # Ignore module/package names starting with an underscore.
            continue

        if module.name.endswith("utils.extensions"):
            # due to circular imports, the utils.extensions cog is not able to utilize the cog metadata class
            # it is hardcoded here as a dev cog in order to prevent it from causing bugs
            yield module.name, BOT_MODES.develop & BOT_MODE
            continue

        imported = importlib.import_module(module.name)
        if module.ispkg:
            if not inspect.isfunction(getattr(imported, "setup", None)):
                # If it lacks a setup function, it's not an extension.
                continue

        if (ext_metadata := getattr(imported, "EXT_METADATA", None)) is not None:
            # check if this cog is dev only or plugin dev only
            load_cog = bool(calc_mode(ext_metadata) & BOT_MODE)
            log.trace(f"Load cog {module.name!r}?: {load_cog}")
            yield module.name, load_cog
            continue

        log.notice(f"Cog {module.name!r} is missing an EXT_METADATA variable. Assuming its a normal cog.")

        yield (module.name, True)


EXTENSIONS = frozenset(walk_extensions())
