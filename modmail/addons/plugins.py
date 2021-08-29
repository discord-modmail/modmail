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
import zipfile
from pathlib import Path
from zipfile import ZipFile

from modmail import plugins
from modmail.addons.errors import NoPluginDirectoryError
from modmail.log import ModmailLogger
from modmail.utils.cogs import ExtMetadata
from modmail.utils.extensions import BOT_MODE, unqualify

logger: ModmailLogger = logging.getLogger(__name__)

VALID_ZIP_PLUGIN_DIRECTORIES = ["plugins", "Plugins"]
BASE_PATH = Path(plugins.__file__).parent.resolve()
PLUGIN_MODULE = "modmail.plugins"
PLUGINS: t.Dict[str, t.Tuple[bool, bool]] = dict()


def find_plugins_in_zip(zip_path: t.Union[str, Path]) -> t.Tuple[t.List[str], t.List[str]]:
    """
    Find the plugins that are in a zip file.

    All plugins in a zip folder will be located at either `Plugins/` or `plugins/`
    """
    archive_plugin_directory = None
    file = ZipFile(zip_path)
    for dir in VALID_ZIP_PLUGIN_DIRECTORIES:
        dir = dir + "/"
        if dir in file.namelist():
            archive_plugin_directory = dir
            break
    if archive_plugin_directory is None:
        raise NoPluginDirectoryError(f"No {' or '.join(VALID_ZIP_PLUGIN_DIRECTORIES)} directory exists.")
    archive_plugin_directory = zipfile.Path(file, at=archive_plugin_directory)
    lil_pluggies = []
    for path in archive_plugin_directory.iterdir():
        logger.debug(f"archive_plugin_directory: {path}")
        if path.is_dir():
            lil_pluggies.append(archive_plugin_directory.name + "/" + path.name + "/")

    logger.debug(f"Plugins detected: {lil_pluggies}")
    all_lil_pluggies = lil_pluggies.copy()
    files = file.namelist()
    for pluggy in all_lil_pluggies:
        for f in files:
            if f == pluggy:
                continue
            if f.startswith(pluggy):
                all_lil_pluggies.append(f)
                print(f)
    logger.trace(f"lil_pluggies: {lil_pluggies}")
    logger.trace(f"all_lil_pluggies: {all_lil_pluggies}")

    return lil_pluggies, all_lil_pluggies


def walk_plugins() -> t.Iterator[t.Tuple[str, bool]]:
    """Yield plugin names from the modmail.plugins subpackage."""
    # walk all files in the plugins folder
    # this is to ensure folder symlinks are supported,
    # which are important for ease of development.
    # NOTE: We are not using Pathlib's glob utility as it doesn't
    #   support following symlinks, see: https://bugs.python.org/issue33428
    for path in glob.iglob(f"{BASE_PATH}/**/*.py", recursive=True):

        logger.trace("Path: {0}".format(path))

        # calculate the module name, dervived from the relative path
        relative_path = Path(path).relative_to(BASE_PATH)
        name = relative_path.__str__().rstrip(".py").replace("/", ".")
        name = PLUGIN_MODULE + "." + name
        logger.trace("Module name: {0}".format(name))

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
            logger.error(
                "Failed to import {0}. As a result, this plugin is not considered installed.".format(name),
                exc_info=True,
            )
            continue

        if not inspect.isfunction(getattr(imported, "setup", None)):
            # If it lacks a setup function, it's not a plugin. This is enforced by dpy.
            logger.trace("{0} does not have a setup function. Skipping.".format(name))
            continue

        ext_metadata: ExtMetadata = getattr(imported, "EXT_METADATA", None)
        if ext_metadata is not None:
            # check if this plugin is dev only or plugin dev only
            load_cog = bool(int(ext_metadata.load_if_mode) & BOT_MODE)
            logger.trace(f"Load plugin {imported.__name__!r}?: {load_cog}")
            yield imported.__name__, load_cog
            continue

        logger.info(
            f"Plugin {imported.__name__!r} is missing a EXT_METADATA variable. Assuming its a normal plugin."
        )

        # Presume Production Mode/Metadata defaults if metadata var does not exist.
        yield imported.__name__, ExtMetadata.load_if_mode
