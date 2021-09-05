# original source:
# https://github.com/python-discord/bot/blob/a8869b4d60512b173871c886321b261cbc4acca9/bot/utils/extensions.py
# MIT License 2021 Python Discord
"""
Helper utililites for managing plugins.

TODO: Expand file to download plugins from github and gitlab from a list that is passed.
"""
from __future__ import annotations

import glob
import importlib
import importlib.util
import inspect
import logging
import os
import pathlib
from typing import Dict, Iterator, List, Tuple

import atoml

from modmail import plugins
from modmail.addons.errors import NoPluginDirectoryError
from modmail.addons.models import Plugin
from modmail.log import ModmailLogger
from modmail.utils.cogs import ExtMetadata
from modmail.utils.extensions import BOT_MODE, unqualify

logger: ModmailLogger = logging.getLogger(__name__)

VALID_ZIP_PLUGIN_DIRECTORIES = ["plugins", "Plugins"]

BASE_PLUGIN_PATH = pathlib.Path(plugins.__file__).parent.resolve()

PLUGINS: Dict[str, Tuple[bool, bool]] = dict()


def parse_plugin_toml_from_string(unparsed_plugin_toml_str: str, /) -> List[Plugin]:
    """Parses a plugin toml, given the string loaded in."""
    doc = atoml.parse(unparsed_plugin_toml_str)
    found_plugins: List[Plugin] = []
    for plug_entry in doc["plugins"]:
        found_plugins.append(
            Plugin(
                plug_entry["name"],
                folder=plug_entry["folder"],
                description=plug_entry["description"],
                min_bot_version=plug_entry["min_bot_version"],
            )
        )
    return found_plugins


def find_plugins_in_dir(addon_repo_path: pathlib.Path) -> Dict[pathlib.Path, List[pathlib.Path]]:
    """
    Find the plugins that are in a directory.

    All plugins in a zip folder will be located at either `Plugins/` or `plugins/`

    Returns a dict containing all of the plugin folders as keys
    and the values as lists of the files within those folders.
    """
    temp_direct_children = [p for p in addon_repo_path.iterdir()]
    if len(temp_direct_children) == 1:
        folder = temp_direct_children[0]
        if folder.is_dir():
            addon_repo_path = addon_repo_path / folder
    del temp_direct_children
    # figure out which directory plugins are in. Both Plugins and plugins are supported.
    # default is plugins.
    plugin_directory = None
    direct_children = [p for p in addon_repo_path.iterdir()]
    logger.debug(f"{direct_children = }")
    for path_ in direct_children:
        if path_.name.rsplit("/", 1)[-1] in VALID_ZIP_PLUGIN_DIRECTORIES:
            plugin_directory = path_
            break

    if plugin_directory is None:
        logger.debug(f"{direct_children = }")
        raise NoPluginDirectoryError(f"No {' or '.join(VALID_ZIP_PLUGIN_DIRECTORIES)} directory exists.")

    plugin_directory = addon_repo_path / plugin_directory

    all_plugins: Dict[pathlib.Path, List[pathlib.Path]] = {}

    for path in plugin_directory.iterdir():
        logger.debug(f"plugin_directory: {path}")
        if path.is_dir():
            all_plugins[path] = list()

    logger.debug(f"Plugins detected: {[p.name for p in all_plugins.keys()]}")

    for plugin_path in all_plugins.keys():
        logger.trace(f"{plugin_path =}")
        for dirpath, dirnames, filenames in os.walk(plugin_path):
            logger.trace(f"{dirpath =}, {dirnames =}, {filenames =}")
            for list_ in dirnames, filenames:
                logger.trace(f"{list_ =}")
                for file in list_:
                    logger.trace(f"{file =}")
                    if file == dirpath:  # don't include files that are plugin directories
                        continue

                    all_plugins[plugin_path].append(pathlib.Path(file))

    logger.debug(f"{all_plugins.keys() = }")
    logger.debug(f"{all_plugins.values() = }")

    return all_plugins


def walk_plugins() -> Iterator[Tuple[str, bool]]:
    """Yield plugin names from the modmail.plugins subpackage."""
    # walk all files in the plugins folder
    # this is to ensure folder symlinks are supported,
    # which are important for ease of development.
    # NOTE: We are not using Pathlib's glob utility as it doesn't
    #   support following symlinks, see: https://bugs.python.org/issue33428
    for path in glob.iglob(f"{BASE_PLUGIN_PATH}/**/*.py", recursive=True):

        logger.trace(f"{path =}")

        # calculate the module name, dervived from the relative path
        relative_path = pathlib.Path(path).relative_to(BASE_PLUGIN_PATH)
        module_name = relative_path.__str__().rstrip(".py").replace("/", ".")
        module_name = plugins.__name__ + "." + module_name
        logger.trace(f"{module_name =}")

        if unqualify(module_name.split(".")[-1]).startswith("_"):
            # Ignore module/package names starting with an underscore.
            continue

        # due to the fact that plugins are user generated and may not have gone through
        # the testing that the bot has, we want to ensure we try/except any plugins
        # that fail to import.
        try:
            # load the plugins using importlib
            # this needs to be done like this, due to the fact that
            # its possible a plugin will not have an __init__.py file
            spec = importlib.util.spec_from_file_location(module_name, path)
            imported = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(imported)
        except Exception:
            logger.error(
                f"Failed to import {module_name}. As a result, this plugin is not considered installed.",
                exc_info=True,
            )
            continue

        if not inspect.isfunction(getattr(imported, "setup", None)):
            # If it lacks a setup function, it's not a plugin. This is enforced by dpy.
            logger.trace(f"{module_name} does not have a setup function. Skipping.")
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
