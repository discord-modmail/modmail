import asyncio
import datetime
import json
import logging
import os
import sys
import typing
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import discord
import toml
from discord.ext.commands import BadArgument
from pydantic import BaseModel
from pydantic import BaseSettings as PydanticBaseSettings
from pydantic import Field, SecretStr
from pydantic.color import Color as ColorBase
from pydantic.env_settings import SettingsSourceCallable
from pydantic.types import conint


log = logging.getLogger(__name__)

CONFIG_PATHS: list = [
    f"{os.getcwd()}/config.toml",
    f"{os.getcwd()}/modmail/config.toml",
    "./config.toml",
]

DEFAULT_CONFIG_PATHS = [os.path.join(os.path.dirname(__file__), "config-default.toml")]


def determine_file_path(
    paths=typing.Union[list, tuple], config_type: str = "default"
) -> typing.Union[str, None]:
    path = None
    for file_path in paths:
        config_file = Path(file_path)
        if (config_file).exists():
            path = config_file
            log.debug(f"Found {config_type} config at {file_path}")
            break
    return path or None


DEFAULT_CONFIG_PATH = determine_file_path(DEFAULT_CONFIG_PATHS)
USER_CONFIG_PATH = determine_file_path(CONFIG_PATHS, config_type="")


def toml_default_config_source(settings: PydanticBaseSettings) -> Dict[str, Any]:
    """
    A simple settings source that loads variables from a toml file
    from within the module's source folder.

    Here we happen to choose to use the `env_file_encoding` from Config
    when reading `config-default.toml`
    """
    return dict(**toml.load(DEFAULT_CONFIG_PATH))


def toml_user_config_source(settings: PydanticBaseSettings) -> Dict[str, Any]:
    """
    A simple settings source that loads variables from a toml file
    from within the module's source folder.

    Here we happen to choose to use the `env_file_encoding` from Config
    when reading `config-default.toml`
    """
    if USER_CONFIG_PATH:
        return dict(**toml.load(USER_CONFIG_PATH))
    else:
        return dict()


class BaseSettings(PydanticBaseSettings):
    class Config:
        extra = "ignore"
        env_file = ".env"
        env_file_encoding = "utf-8"

        @classmethod
        def customise_sources(
            cls,
            init_settings: SettingsSourceCallable,
            env_settings: SettingsSourceCallable,
            file_secret_settings: SettingsSourceCallable,
        ) -> Tuple[SettingsSourceCallable, ...]:
            return (
                env_settings,
                init_settings,
                file_secret_settings,
                toml_user_config_source,
                toml_default_config_source,
            )


class BotConfig(BaseSettings):
    prefix: str = "?"
    token: str = None

    class Config:
        # env_prefix = "bot."
        allow_mutation = False


class BotMode(BaseSettings):
    """
    Bot mode.

    Used to determine when the bot will run.
    """

    production: bool = True
    plugin_dev: bool = False
    develop: bool = False


class Colors(BaseSettings):
    """
    Default colors.

    These should only be changed here to change the default colors.
    """

    embed_color: ColorBase = "0087BD"


class DevConfig(BaseSettings):
    """
    Developer specific configuration.
    These settings should not be changed unless you know what you're doing.
    """

    log_level: conint(ge=0, le=50) = getattr(logging, "NOTICE", 25)
    mode: BotMode


class ModmailConfig(BaseSettings):
    bot: BotConfig
    dev: DevConfig
    colors: Colors


CONFIG = ModmailConfig()
