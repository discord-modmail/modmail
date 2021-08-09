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
from modmail.log import ModmailLogger
from modmail.utils.cogs import ExtMetadata
from modmail.utils.extensions import BOT_MODE, unqualify

BASE_PATH = Path(plugins.__file__).parent

log: ModmailLogger = logging.getLogger(__name__)

PLUGINS = dict()


def walk_plugins() -> Iterator[str]:
    """Yield plugin names from the modmail.plugins subpackage."""
    for path in BASE_PATH.glob("**/*.py"):
        # calculate the module name, if it were to have a name from the path
        relative_path = path.relative_to(BASE_PATH)
        name = relative_path.__str__().rstrip(".py").replace("/", ".")
        name = "modmail.plugins." + name
        log.trace("Relative path: {0}".format(name))

        if unqualify(name.split(".")[-1]).startswith("_"):
            # Ignore module/package names starting with an underscore.
            continue

        # load the plugins using importlib
        # this needs to be done like this, due to the fact that
        # its possible a plugin will not have an __init__.py file
        spec = importlib.util.spec_from_file_location(name, path)
        imported = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(imported)

        if not inspect.isfunction(getattr(imported, "setup", None)):
            # If it lacks a setup function, it's not a plugin. This is enforced by dpy.
            continue

        ext_metadata: ExtMetadata = getattr(imported, "EXT_METADATA", None)
        if ext_metadata is not None:
            # check if this plugin is dev only or plugin dev only
            load_cog = (ext_metadata.load_if_mode & BOT_MODE).to_strings()
            log.trace(f"Load plugin {imported.__name__!r}?: {load_cog}")
            yield imported.__name__, load_cog
            continue

        log.info(
            f"Plugin {imported.__name__!r} is missing a EXT_METADATA variable. Assuming its a normal plugin."
        )

        yield imported.__name__, True
