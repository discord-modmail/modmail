# original source:
# https://github.com/python-discord/bot/blob/a8869b4d60512b173871c886321b261cbc4acca9/bot/utils/extensions.py
# MIT License 2021 Python Discord
"""
Helper utililites for managing plugins.

TODO: Expand file to download plugins from github and gitlab from a list that is passed.
"""


import glob
import importlib
import importlib.util
import inspect
import logging
import typing as t
from pathlib import Path

from modmail import plugins
from modmail.log import ModmailLogger
from modmail.utils.cogs import ExtMetadata
from modmail.utils.extensions import BOT_MODE, unqualify

log: ModmailLogger = logging.getLogger(__name__)


BASE_PATH = Path(plugins.__file__).parent.resolve()
PLUGIN_MODULE = "modmail.plugins"
PLUGINS: t.Dict[str, t.Tuple[bool, bool]] = dict()


def walk_plugins() -> t.Iterator[t.Tuple[str, bool]]:
    """Yield plugin names from the modmail.plugins subpackage."""
    # walk all files in the plugins folder
    # this is to ensure folder symlinks are supported,
    # which are important for ease of development.
    # NOTE: We are not using Pathlib's glob utility as it doesn't
    #   support following symlinks, see: https://bugs.python.org/issue33428
    for path in glob.iglob(f"{BASE_PATH}/**/*.py", recursive=True):

        log.trace("Path: {0}".format(path))

        # calculate the module name, dervived from the relative path
        relative_path = Path(path).relative_to(BASE_PATH)
        name = relative_path.__str__().rstrip(".py").replace("/", ".")
        name = PLUGIN_MODULE + "." + name
        log.trace("Module name: {0}".format(name))

        if unqualify(name.split(".")[-1]).startswith("_"):
            # Ignore module/package names starting with an underscore.
            continue

        # due to the fact that plugins are user generated and may not have gone through
        # the testing that the bot has, we want to ensure we try/except any plugins
        # that fail to import.
        try:
            # load the plugins using importlib
            # this needs to be done like this, due to the fact that
            # its possible a plugin will not have an __init__.py file
            spec = importlib.util.spec_from_file_location(name, path)
            imported = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(imported)
        except Exception:
            log.error(
                "Failed to import {0}. As a result, this plugin is not considered installed.".format(name),
                exc_info=True,
            )
            continue

        if not inspect.isfunction(getattr(imported, "setup", None)):
            # If it lacks a setup function, it's not a plugin. This is enforced by dpy.
            log.trace("{0} does not have a setup function. Skipping.".format(name))
            continue

        ext_metadata: ExtMetadata = getattr(imported, "EXT_METADATA", None)
        if ext_metadata is not None:
            # check if this plugin is dev only or plugin dev only
            load_cog = bool(int(ext_metadata.load_if_mode) & BOT_MODE)
            log.trace(f"Load plugin {imported.__name__!r}?: {load_cog}")
            yield imported.__name__, load_cog
            continue

        log.info(
            f"Plugin {imported.__name__!r} is missing a EXT_METADATA variable. Assuming its a normal plugin."
        )

        # Presume Production Mode/Metadata defaults if metadata var does not exist.
        yield imported.__name__, ExtMetadata.load_if_mode
