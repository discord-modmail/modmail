# initial source:
# https://github.com/python-discord/bot/blob/a8869b4d60512b173871c886321b261cbc4acca9/bot/utils/extensions.py
# MIT License 2021 Python Discord
import importlib
import inspect
import logging
import pkgutil
from typing import Dict, Generator, List, NewType, NoReturn, Tuple

from modmail import extensions
from modmail.log import ModmailLogger
from modmail.utils.cogs import BOT_MODE, BotModeEnum, ExtMetadata


log: ModmailLogger = logging.getLogger(__name__)

EXT_METADATA = ExtMetadata

ModuleName = NewType("ModuleName", str)
ModuleDict = Dict[ModuleName, ExtMetadata]

EXTENSIONS: ModuleDict = dict()
NO_UNLOAD: List[ModuleName] = list()


def unqualify(name: str) -> str:
    """Return an unqualified name given a qualified module/package `name`."""
    return name.rsplit(".", maxsplit=1)[-1]


log.trace(f"BOT_MODE value: {BOT_MODE}")
log.debug(f"Dev mode status: {bool(BOT_MODE & BotModeEnum.DEVELOP)}")
log.debug(f"Plugin dev mode status: {bool(BOT_MODE & BotModeEnum.PLUGIN_DEV)}")


def walk_extensions() -> Generator[Tuple[ModuleName, ExtMetadata], None, None]:
    """Yield extension names from the modmail.exts subpackage."""

    def on_error(name: str) -> NoReturn:
        raise ImportError(name=name)  # pragma: no cover

    for module in pkgutil.walk_packages(extensions.__path__, f"{extensions.__name__}.", onerror=on_error):
        if unqualify(module.name).startswith("_"):
            # Ignore module/package names starting with an underscore.
            continue

        imported = importlib.import_module(module.name)
        if not inspect.isfunction(getattr(imported, "setup", None)):
            # If it lacks a setup function, it's not an extension.
            continue

        ext_metadata: ExtMetadata = getattr(imported, "EXT_METADATA", None)
        if ext_metadata is not None:
            if not isinstance(ext_metadata, ExtMetadata):
                if ext_metadata == ExtMetadata:
                    log.info(
                        f"{module.name!r} seems to have passed the ExtMetadata class directly to "
                        "EXT_METADATA. Using defaults."
                    )
                else:
                    log.error(
                        f"Extension {module.name!r} contains an invalid EXT_METADATA variable. "
                        "Loading with metadata defaults. Please report this bug to the developers."
                    )
                yield module.name, ExtMetadata()
                continue

            log.debug(f"{module.name!r} contains a EXT_METADATA variable. Loading it.")

            yield module.name, ext_metadata
            continue

        log.notice(
            f"Extension {module.name!r} is missing an EXT_METADATA variable. Assuming its a normal extension."
        )

        # Presume Production Mode/Metadata defaults if metadata var does not exist.
        yield module.name, ExtMetadata()
