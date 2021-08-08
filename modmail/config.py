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


class ThreadBaseSettings(BaseSettings):
    class Config:
        env_prefix = "thread."

        # @classmethod
        # def alias_generator(cls, string: str) -> str:
        #     return f"thread.{super.__name__}.{string}"


class BotActivityConfig(BaseSettings):
    twitch_url: str = "https://www.twitch.tv/discordmodmail/"


class BotConfig(BaseSettings):
    prefix: str = "?"
    activity: BotActivityConfig
    token: str = None
    modmail_guild_id: str = None
    guild_id: str = None
    multi_bot: bool = False
    log_url: str = None
    log_url_prefix = "/"
    github_token: SecretStr = None
    database_type: str = "mongodb"  # TODO limit to specific strings
    enable_plugins: bool = True
    enable_eval: bool = True
    data_collection = True
    owners: str = 1
    connection_uri: str = None
    level_permissions: dict = None

    class Config:
        # env_prefix = "bot."
        allow_mutation = False


class ColorsConfig(BaseSettings):
    main_color: str = str(discord.Colour.blurple())
    error_color: str = str(discord.Colour.red())
    recipient_color: str = str(discord.Colour.green())
    mod_color: str = str(discord.Colour.blue())


class ChannelConfig(BaseSettings):
    # all of the below should be validated to channels
    # either by name or by int
    main_category: str = None
    fallback_category: str = None
    log_channel: str = None
    mention_channel: str = None
    update_channel: str = None


class BotMode(BaseSettings):
    """
    Bot mode.

    Used to determine when the bot will run.
    """

    production: bool = True
    plugin_dev: bool = False
    develop: bool = False


class DevConfig(BaseSettings):
    """
    Developer specific configuration.
    These settings should not be changed unless you know what you're doing.
    """

    log_level: conint(ge=0, le=50) = getattr(logging, "NOTICE", 25)
    mode: BotMode


class EmojiConfig(BaseSettings):
    """
    Standard emojis that the bot uses when a specific emoji is not defined for a specific use.
    """

    sent_emoji: str = "\\N{WHITE HEAVY CHECK MARK}"  # TODO type as a discord emoji
    blocked_emoji: str = "\\N{NO ENTRY SIGN}"  # TODO type as a discord emoji


class InternalConfig(BaseModel):
    # do NOT set these yourself. The bot will handle these
    activity_message: str = None
    activity_type: None = None
    status: None = None
    dm_disabled: int = 0
    # moderation
    blocked: dict = dict()
    blocked_roles: dict = dict()
    blocked_whitelist: list = dict()
    command_permissions: dict = dict()
    level_permissions: dict = dict()
    override_command_level: dict = dict()
    # threads
    snippets: dict = dict()
    notifications: dict = dict()
    subscriptions: dict = dict()
    closures: dict = dict()
    # misc
    plugins: list = list()
    aliases: dict = dict()
    auto_triggers: dict = dict()
    command_permissions: dict = dict()
    level_permissions: dict = dict()

    class Config:
        arbitrary_types_allowed = True


class MentionConfig(BaseSettings):
    alert_on_mention: bool = False
    silent_alert_on_mention: bool = False
    mention_channel: int = None


class SnippetConfig(BaseSettings):
    anonmous_snippets: bool = False
    use_regex_autotrigger: bool = False


class ThreadAnonConfig(ThreadBaseSettings):
    username: str = "Response"
    footer: str = "Staff Team"


class ThreadAutoCloseConfig(ThreadBaseSettings):
    time: datetime.timedelta = 0
    silently: bool = False
    response: str = "This thread has been closed automatically due to inactivity after {timeout}."


class ThreadCloseConfig(ThreadBaseSettings):
    footer: str = "Replying will create a new thread"
    title: str = "Thread Closed"
    response: str = "{closer.mention} has closed this Modmail thread."
    on_leave: bool = False
    on_leave_reason: str = "The recipient has left the server."
    self_close_response: str = "You have closed this Modmail thread."


class ThreadConfirmCreationConfig(ThreadBaseSettings):
    enabled: bool = False
    title: str = "Confirm thread creation"
    response: str = "React to confirm thread creation which will directly contact the moderators"
    accept_emoji: str = "\N{WHITE HEAVY CHECK MARK}"  # TODO type as a discord emoji
    deny_emoji: str = "\N{NO ENTRY SIGN}"  # TODO type as a discord emoji


class ThreadCooldownConfig(ThreadBaseSettings):
    time: datetime.timedelta = 0
    embed_title: str = "Message not sent!"
    response: str = "You must wait for {delta} before you can contact me again."


class ThreadCreationConfig(ThreadBaseSettings):
    response: str = "The staff team will get back to you as soon as possible."
    footer: str = "Your message has been sent"
    title: str = "Thread Created"


class ThreadDisabledConfig(ThreadBaseSettings):
    new_title: str = "Not Delivered"
    new_response: str = "We are not accepting new threads."
    new_footer: str = "Please try again later..."
    current_title: str = "Not Delivered"
    current_response: str = "We are not accepting any messages."
    current_footer: str = "Please try again later..."


class ThreadMoveConfig(ThreadBaseSettings):
    title: str = "Thread Moved"
    notify: bool = False
    notify_mods: bool = False
    response: str = "This thread has been moved."


class ThreadSelfClosableConfig(ThreadBaseSettings):
    enabled: bool = False
    lock_emoji: str = "\N{LOCK}"
    creation_footer: str = "Click the lock to close the thread"


class ThreadConfig(BaseSettings):
    anon_reply_without_command: bool = False
    reply_without_command: bool = False
    plain_reply_without_command: bool = False
    mention: str = "@here"
    user_typing: bool = False
    mod_typing: bool = False
    transfer_reactions: bool = True
    contact_silently: bool = False
    account_age: datetime.timedelta = 0
    guild_age: datetime.timedelta = 0
    mod_tag: str = ""
    show_timestamp: bool = True

    anon: ThreadAnonConfig
    auto_close: ThreadAutoCloseConfig
    close: ThreadCloseConfig
    confirm_creation: ThreadConfirmCreationConfig
    cooldown: ThreadCooldownConfig
    creation: ThreadCreationConfig
    disabled: ThreadDisabledConfig
    move: ThreadMoveConfig
    self_closable: ThreadSelfClosableConfig


class UpdateConfig(BaseSettings):
    disable_autoupdates: bool = False
    update_notifications: bool = True

    class Config:
        allow_mutation = False
        env_prefix = "updates."


class ModmailConfig(BaseSettings):
    bot: BotConfig
    colors: ColorsConfig
    channels: ChannelConfig
    dev: DevConfig
    emoji: EmojiConfig
    mention: MentionConfig
    snippets: SnippetConfig
    thread: ThreadConfig
    updates: UpdateConfig
    shell: str = None


CONFIG = ModmailConfig()
INTERNAL = InternalConfig()
