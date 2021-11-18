# original source:
# https://github.com/python-discord/bot/blob/a8869b4d60512b173871c886321b261cbc4acca9/bot/utils/extensions.py
# MIT License 2021 Python Discord
"""
Helper utililites for managing plugins.

TODO: Expand file to download plugins from github and gitlab from a list that is passed.
"""
from __future__ import annotations

import asyncio
import glob
import importlib
import importlib.util
import inspect
import logging
import os
import pathlib
import sys
from asyncio import subprocess
from collections.abc import Generator
from typing import List, Optional, Set, Tuple

import atoml

from modmail import plugins
from modmail.addons.errors import NoPluginDirectoryError, NoPluginTomlFoundError
from modmail.addons.models import Plugin
from modmail.log import ModmailLogger
from modmail.utils.cogs import ExtMetadata
from modmail.utils.extensions import ModuleName, unqualify


__all__ = [
    "VALID_ZIP_PLUGIN_DIRECTORIES",
    "BASE_PLUGIN_PATH",
    "PLUGINS",
    "PLUGIN_TOML",
    "LOCAL_PLUGIN_TOML",
    "parse_plugin_toml_from_string",
    "update_local_toml_enable_or_disable",
    "find_partial_plugins_from_dir",
    "find_plugins",
    "walk_plugin_files",
]


logger: ModmailLogger = logging.getLogger(__name__)

VALID_ZIP_PLUGIN_DIRECTORIES = ["plugins", "Plugins"]

BASE_PLUGIN_PATH = pathlib.Path(plugins.__file__).parent.resolve()

PLUGINS: Set[Plugin] = set()

PLUGIN_TOML = "plugin.toml"

LOCAL_PLUGIN_TOML = BASE_PLUGIN_PATH / "local.toml"

PYTHON_INTERPRETER: Optional[str] = sys.executable

PIP_NO_ROOT_WARNING = (
    "WARNING: Running pip as the 'root' user can result in broken permissions and "
    "conflicting behaviour with the system package manager. "
    "It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv"
).encode()


async def install_dependencies(plugin: Plugin) -> str:
    """Installs provided dependencies from a plugin."""
    # check if there are any plugins to install
    if not len(plugin.dependencies):
        return

    if PYTHON_INTERPRETER is None:
        raise FileNotFoundError("Could not locate python interpreter.")

    # This uses the check argument with our exported requirements.txt
    # to make pip promise that anything it installs won't change
    # the packages that the bot requires to have installed.
    pip_install_args = [
        "-m",
        "pip",
        "--no-input",
        "--no-color",
        "install",
        "--constraint",
        str(BASE_PLUGIN_PATH.parent / "constraints.txt"),
    ]
    proc = await asyncio.create_subprocess_exec(
        PYTHON_INTERPRETER,
        *pip_install_args,
        *plugin.dependencies,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    logger.debug(f"{stdout.decode() = }")

    if stderr:
        stderr = stderr.replace(PIP_NO_ROOT_WARNING, b"").strip()
        if len(stderr.decode()) > 0:
            logger.error(f"Received stderr: '{stderr.decode()}'")
            raise Exception("Something went wrong when installing.")
    return stdout.decode()


def parse_plugin_toml_from_string(unparsed_plugin_toml_str: str, /, local: bool = False) -> List[Plugin]:
    """Parses a plugin toml, given the string loaded in."""
    doc = atoml.parse(unparsed_plugin_toml_str)
    found_plugins: List[Plugin] = []
    for plug_entry in doc["plugins"]:
        if local:
            enabled = plug_entry.get("enabled", True)
        else:
            enabled = None
        found_plugins.append(
            Plugin(
                plug_entry.get("directory") or plug_entry["folder"],
                name=plug_entry.get("name"),
                description=plug_entry.get("description"),
                min_bot_version=plug_entry.get("min_bot_version"),
                enabled=enabled,
                dependencies=plug_entry.get("dependencies"),
            )
        )
    return found_plugins


def update_local_toml_enable_or_disable(plugin: Plugin, /) -> None:
    """
    Updates the local toml so local plugins stay disabled or enabled.

    This is the local implementation for disabling and enabling to actually disable and enable plugins.
    Non local plugins are saved in the database.
    """
    if not LOCAL_PLUGIN_TOML.exists():
        raise NoPluginTomlFoundError(
            f"The required file at {LOCAL_PLUGIN_TOML!s} does not exist to deal with local plugins.\n"
            "You may need to create it."
        )

    with LOCAL_PLUGIN_TOML.open("r") as f:
        doc = atoml.loads(f.read())
    plugs = doc["plugins"]

    plug_found = False
    for plug_entry in plugs:
        folder_name = plug_entry.get("directory") or plug_entry["folder"]
        if folder_name == plugin.folder_name:
            plug_entry["enabled"] = plugin.enabled
            plug_found = True
            break

    if not plug_found:
        # need to write a new entry
        logger.trace(f"Local plugin toml does not contain an entry for {plugin}")

        plugin_table = atoml.table()
        if plugin.name != plugin.folder_name:
            plugin_table.add("name", atoml.item(plugin.name))

        plugin_table.add("directory", atoml.item(plugin.folder_name))
        plug_entry["enabled"] = plugin.enabled
        plugs.append(plugin_table)
        print(plugs)

    with open(LOCAL_PLUGIN_TOML, "w") as f:
        f.write(doc.as_string())


def find_partial_plugins_from_dir(
    addon_repo_path: pathlib.Path,
    *,
    parse_toml: bool = True,
    no_toml_exist_ok: bool = True,
) -> Generator[Plugin, None, None]:
    """
    Find the plugins that are in a directory.

    All plugins in a zip folder will be located at either `Plugins/` or `plugins/`

    If parse_toml is true, if the plugin.toml file is found, it will be parsed.

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

    all_plugins: Set[Plugin] = set()

    if parse_toml:
        toml_path = plugin_directory / PLUGIN_TOML
        if toml_path.exists():
            # parse the toml
            with open(toml_path) as toml_file:
                all_plugins.update(parse_plugin_toml_from_string(toml_file.read()))

        elif no_toml_exist_ok:
            # toml does not exist but the caller does not care
            pass
        else:
            raise NoPluginTomlFoundError(toml_path, "does not exist")

    logger.debug(f"{all_plugins =}")
    for path in plugin_directory.iterdir():
        logger.debug(f"plugin_directory: {path}")
        if path.is_dir():
            # use an existing toml plugin object
            if path.name in all_plugins:
                for p in all_plugins:
                    if p.folder_name == path.name:
                        p.folder_path = path
                        yield p
                        break
            else:
                logger.debug(
                    f"Plugin in {addon_repo_path!s} is not provided in toml. Creating new plugin object."
                )
                yield Plugin(path.name, folder_path=path)


def find_plugins(
    detection_path: pathlib.Path = None, /, *, local: Optional[bool] = True
) -> Generator[Plugin, None, None]:
    """
    Walks the local path, and determines which files are local plugins.

    Yields a list of plugins,
    """
    if detection_path is None:
        detection_path = BASE_PLUGIN_PATH
    all_plugins: Set[Plugin] = set()

    toml_plugins: List[Plugin] = []
    toml_path = LOCAL_PLUGIN_TOML
    if toml_path.exists():
        # parse the toml
        with open(toml_path) as toml_file:
            toml_plugins = parse_plugin_toml_from_string(toml_file.read(), local=True)
    else:
        raise NoPluginTomlFoundError(toml_path, "does not exist")

    logger.debug(f"{toml_plugins =}")
    toml_plugin_names = [p.folder_name for p in toml_plugins]
    for path in detection_path.iterdir():
        logger.debug(f"detection_path / path: {path}")
        if path.is_dir():
            # use an existing toml plugin object
            if path.name in toml_plugin_names:
                for p in toml_plugins:
                    if p.folder_name == path.name:
                        p.folder_path = path
                        all_plugins.add(p)

    logger.debug(f"Local plugins detected: {[p.name for p in all_plugins]}")

    for plugin_ in all_plugins:
        logger.trace(f"{plugin_.folder_path =}")
        if local is not None:
            # configure all plugins with the provided local variable
            plugin_.local = local
        for dirpath, dirnames, filenames in os.walk(plugin_.folder_path):
            logger.trace(f"{dirpath =}, {dirnames =}, {filenames =}")
            for list_ in dirnames, [dirpath]:
                logger.trace(f"{list_ =}")
                for dir_ in list_:
                    logger.trace(f"{dir_ =}")

                    if "__pycache__" in dir_ or "__pycache__" in dirpath:
                        continue

                    plugin_.modules = {}
                    plugin_.modules.update(walk_plugin_files(dirpath))
                    yield plugin_

    logger.debug(f"{all_plugins = }")


def walk_plugin_files(
    detection_path: pathlib.Path = None,
) -> Generator[Tuple[ModuleName, ExtMetadata], None, None]:
    """Yield plugin names from the modmail.plugins subpackage."""
    # walk all files in the plugins folder
    # this is to ensure folder symlinks are supported,
    # which are important for ease of development.
    # NOTE: We are not using Pathlib's glob utility as it doesn't
    #   support following symlinks, see: https://bugs.python.org/issue33428
    if detection_path is None:
        detection_path = BASE_PLUGIN_PATH
    for path in glob.iglob(f"{detection_path}/**/*.py", recursive=True):

        logger.trace(f"{path =}")

        # calculate the module name, dervived from the relative path
        relative_path = pathlib.Path(path).relative_to(BASE_PLUGIN_PATH)
        module_name = ".".join(relative_path.parent.parts) + "." + relative_path.stem
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
            if not isinstance(ext_metadata, ExtMetadata):
                if ext_metadata == ExtMetadata:
                    logger.info(
                        f"{imported.__name__!r} seems to have passed the ExtMetadata class directly to "
                        "EXT_METADATA. Using defaults."
                    )
                else:
                    logger.error(
                        f"Plugin extension {imported.__name__!r} contains an invalid EXT_METADATA variable. "
                        "Loading with metadata defaults. Please report this bug to the developers."
                    )
                yield imported.__name__, ExtMetadata()
                continue

            logger.debug(f"{imported.__name__!r} contains a EXT_METADATA variable. Loading it.")

            yield imported.__name__, ext_metadata
            continue

        logger.notice(
            f"Plugin extension {imported.__name__!r} is missing an EXT_METADATA variable. "
            "Assuming its a normal plugin extension."
        )

        # Presume Production Mode/Metadata defaults if metadata var does not exist.
        yield imported.__name__, ExtMetadata()
