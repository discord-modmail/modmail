# original source:
# https://github.com/python-discord/bot/blob/a8869b4d60512b173871c886321b261cbc4acca9/bot/utils/extensions.py
# MIT License 2021 Python Discord
"""
Helper utililites for managing plugins.

TODO: Expand file to download plugins from github and gitlab from a list that is passed.
"""


import importlib
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Iterator

from modmail import plugins
from modmail.config import CONFIG
from modmail.log import ModmailLogger
from modmail.utils.cogs import calc_mode

BOT_MODE = calc_mode(CONFIG.dev)
BASE_PATH = Path(plugins.__file__).parent


log: ModmailLogger = logging.getLogger(__name__)
log.trace(f"BOT_MODE value: {BOT_MODE}")


def unqualify(name: str) -> str:
    """Return an unqualified name given a qualified module/package `name`."""
    return name.rsplit(".", maxsplit=1)[-1]


def walk_plugins() -> Iterator[str]:
    """Yield plugin names from the modmail.plugins subpackage."""
    for path in BASE_PATH.glob("*/*.py"):
        # calculate the module name, if it were to have a name from the path
        relative_path = path.relative_to(BASE_PATH)
        name = relative_path.__str__().rstrip(".py").replace("/", ".")
        name = "modmail.plugins." + name
        log.trace("Relative path: {0}".format(name))

        spec = importlib.util.spec_from_file_location(name, path)
        imported = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(imported)

        if not inspect.isfunction(getattr(imported, "setup", None)):
            # If it lacks a setup function, it's not an plugin.
            continue

        if (ext_metadata := getattr(imported, "EXT_METADATA", None)) is not None:
            # check if this plugin is dev only or plugin dev only
            load_cog = bool(calc_mode(ext_metadata) & BOT_MODE)
            log.trace(f"Load plugin {imported.__name__!r}?: {load_cog}")
            yield imported.__name__, load_cog
            continue

        log.notice(
            f"Plugin {imported.__name__!r} is missing a EXT_METADATA variable. Assuming its a normal plugin."
        )

        yield (imported.__name__, True)


PLUGINS = frozenset(walk_plugins())
