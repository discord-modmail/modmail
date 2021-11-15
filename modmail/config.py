import inspect
import logging
import os
import pathlib
import types
import typing
from collections import defaultdict

import attr
import desert
import discord
import discord.ext.commands
import discord.ext.commands.converter
import dotenv
import marshmallow
import marshmallow.fields
import marshmallow.validate


try:
    import atoml
except ModuleNotFoundError:  # pragma: nocover
    atoml = None
try:
    import yaml
except ModuleNotFoundError:  # pragma: nocover
    yaml = None

__all__ = [
    "AUTO_GEN_FILE_NAME",
    "ENV_PREFIX",
    "USER_CONFIG_FILE_NAME",
    "USER_CONFIG_FILES",
    "CfgLoadError",
    "Config",
    "config",
    "ConfigurationSchema",
    "BotCfg",
    "BotModeCfg",
    "Cfg",
    "Colours",
    "DevCfg",
    "convert_to_color",
    "get_config",
    "get_default_config",
    "load_env",
    "load_toml",
    "load_yaml",
]

_CWD = pathlib.Path.cwd()
METADATA_TABLE = "modmail_metadata"
ENV_PREFIX = "MODMAIL_"
USER_CONFIG_FILE_NAME = "modmail_config"
AUTO_GEN_FILE_NAME = "default_config"
USER_CONFIG_FILES = [
    _CWD / (USER_CONFIG_FILE_NAME + ".yaml"),
    _CWD / (USER_CONFIG_FILE_NAME + ".toml"),
]


class BetterPartialEmojiConverter(discord.ext.commands.converter.EmojiConverter):
    """
    Converts to a :class:`~discord.PartialEmoji`.

    This is done by extracting the animated flag, name and ID from the emoji.
    """

    async def convert(self, _: discord.ext.commands.context.Context, argument: str) -> discord.PartialEmoji:
        # match = self._get_id_match(argument) or re.match(
        #     r"<a?:[a-zA-Z0-9\_]{1,32}:([0-9]{15,20})>$", argument
        # )

        match = discord.PartialEmoji._CUSTOM_EMOJI_RE.match(argument)
        if match is not None:
            groups = match.groupdict()
            animated = bool(groups["animated"])
            emoji_id = int(groups["id"])
            name = groups["name"]
            return discord.PartialEmoji(name=name, animated=animated, id=emoji_id)

        return discord.PartialEmoji(name=argument)


# load env before we do *anything*
# TODO: Convert this to a function and check the parent directory too, if the CWD is within the bot.
# TODO: add the above feature to the other configuration locations too.
dotenv.load_dotenv(_CWD / ".env")


def _generate_default_dict() -> defaultdict:
    """For defaultdicts to default to a defaultdict."""
    return defaultdict(_generate_default_dict)


class CfgLoadError(Exception):
    """Exception if the configuration failed to load from a local file."""

    ...


class _ColourField(marshmallow.fields.Field):
    """Class to convert a str or int into a color and deserialize into a string."""

    class ColourConvert(discord.ext.commands.converter.ColourConverter):
        """Inherited discord.py colour converter."""

        def convert(self, argument: typing.Union[str, int, discord.Colour]) -> discord.Colour:
            """
            Convert an argument into a discord.Colour.

            This code was copied from discord.ext.commands.converter.ColourConverter.
            Modified to not be async or need a context since it was not used in the first place.
            """
            if isinstance(argument, discord.Colour):
                return argument
            if not isinstance(argument, str):
                argument = str(argument)

            if argument[0] == "#":
                return self.parse_hex_number(argument[1:])

            if argument[0:2] == "0x":
                rest = argument[2:]
                # Legacy backwards compatible syntax
                if rest.startswith("#"):
                    return self.parse_hex_number(rest[1:])
                return self.parse_hex_number(rest)

            arg = argument.lower()
            if arg[0:3] == "rgb":
                return self.parse_rgb(arg)

            arg = arg.replace(" ", "_")
            method = getattr(discord.Colour, arg, None)
            if arg.startswith("from_") or method is None or not inspect.ismethod(method):
                raise discord.ext.commands.converter.BadColourArgument(arg)
            return method()

    def _serialize(self, value: discord.Colour, attr: str, obj: typing.Any, **kwargs) -> str:
        return "#" + hex(value.value)[2:].lower()

    def _deserialize(
        self,
        value: typing.Any,
        attr: typing.Optional[str],
        data: typing.Optional[typing.Mapping[str, typing.Any]],
        **kwargs,
    ) -> discord.Colour:
        if not isinstance(value, discord.Colour):
            value = self.ColourConvert().convert(value)
        return value


def convert_to_color(col: typing.Union[str, int, discord.Colour]) -> discord.Colour:
    """Convert a string or integer to a discord.Colour. Also supports being passed a discord.Colour."""
    return _ColourField.ColourConvert().convert(col)


@attr.frozen(kw_only=True)
class ConfigMetadata:
    """
    Cfg metadata. This is intended to be used on the marshmallow and attr metadata dict as 'modmail_metadata'.

    Nearly all of these values are optional, save for the description.
    All of them are keyword only.
    In addition, all instances of this class are frozen; they are not meant to be changed after creation.

    These values are meant to be used for the configuration UI and exports.
    In relation to that, most are optional. However, *all* instances must have a description.
    """

    # what to refer to for the end user
    description: str = attr.ib()
    canonical_name: str = None
    # for those configuration options where the description just won't cut it.
    extended_description: str = None
    # for the variables to export to the environment, what value should be prefilled
    export_environment_prefill: str = None
    # comment provided above or beside the default configuration option in exports
    export_note: str = None
    # this only has an effect if required is not True
    # required variables will always be exported, but if this is a commonly changed var, this should be True.
    export_to_env_template: bool = False

    # app json is slightly different, so there's additional options for them
    export_to_app_json: bool = None
    app_json_default: str = None
    app_json_required: bool = None

    # I have no plans to add async to this file, that would make it overly complex.
    # as a solution, I'm implementing a field which can provide a rich converter object,
    # in the style that discord.py uses. This will be called like discord py calls.
    discord_converter: discord.ext.commands.converter.Converter = attr.ib(default=None)
    discord_converter_attribute: typing.Optional[
        types.FunctionType
    ] = None  # if we want an attribute off of the converted value

    # hidden, eg log_level
    # hidden values mean they do not show up in the bot configuration menu
    hidden: bool = False

    @description.validator
    def _validate_description(self, attrib: attr.Attribute, value: typing.Any) -> None:
        if not isinstance(value, attrib.type):  # pragma: no branch
            raise ValueError(f"description must be of {attrib.type}") from None

    @discord_converter.validator
    def _validate_discord_converter(self, attrib: attr.Attribute, value: typing.Any) -> None:
        if value is None:
            return
        if not hasattr(value, "convert"):  # pragma: no branch
            raise AttributeError("Converters must have a method named convert.")


@attr.s(auto_attribs=True, slots=True)
class BotCfg:
    """
    Values that are configuration for the bot itself.

    These are metavalues, and are the token, prefix, database bind, basically all of the stuff that needs to
    be known BEFORE attempting to log in to the database or discord.
    """

    token: str = attr.ib(
        default=marshmallow.missing,
        on_setattr=attr.setters.frozen,
        repr=False,
        metadata={
            "required": True,
            "dump_only": True,
            "allow_none": False,
            METADATA_TABLE: ConfigMetadata(
                canonical_name="Bot Token",
                description="Discord bot token. Required to log in to discord.",
                export_environment_prefill="Bot Token",
                extended_description="This is obtainable from https://discord.com/developers/applications",
                export_to_env_template=True,
            ),
        },
    )
    prefix: str = attr.ib(
        default="?",
        metadata={
            METADATA_TABLE: ConfigMetadata(
                canonical_name="Command Prefix",
                description="Command prefix.",
                export_environment_prefill="?",
                app_json_default="?",
                app_json_required=False,
                export_to_env_template=True,
            )
        },
    )
    prefix_when_mentioned: bool = attr.ib(
        default=True,
        metadata={
            METADATA_TABLE: ConfigMetadata(description="Use the bot mention as a prefix."),
        },
    )


@attr.s(auto_attribs=True, slots=True, frozen=True)
class BotModeCfg:
    """
    The three bot modes for the bot. Enabling some of these may enable other bot features.

    `production` is used internally and is always True.
    `develop` enables additional features which are useful for bot developers.
    `plugin_dev` enables additional commands which are useful when working with plugins.
    """

    production: bool = desert.ib(
        marshmallow.fields.Constant(True),
        default=True,
        converter=lambda _: True,
        metadata={
            "dump_default": True,
            "dump_only": True,
            METADATA_TABLE: ConfigMetadata(
                description="Production Mode. This is not changeable.",
            ),
        },
    )
    develop: bool = attr.ib(
        default=False,
        metadata={
            "allow_none": False,
            METADATA_TABLE: ConfigMetadata(
                description="Bot developer mode. Enables additional developer specific features.",
            ),
        },
    )
    plugin_dev: bool = attr.ib(
        default=False,
        metadata={
            "allow_none": False,
            METADATA_TABLE: ConfigMetadata(
                description="Plugin developer mode. Enables additional plugin developer specific features.",
            ),
        },
    )


@attr.s(auto_attribs=True, slots=True)
class Colours:
    """
    Default colors.

    These should only be changed here to change the default colors.
    """

    base_embed_color: discord.Colour = desert.ib(
        _ColourField(),
        default="0x7289DA",
        converter=convert_to_color,
        metadata={
            METADATA_TABLE: ConfigMetadata(
                description="Default embed colour for all embeds without a designated colour.",
            )
        },
    )


@attr.s(auto_attribs=True, slots=True)
class DevCfg:
    """Developer configuration. These values should not be changed unless you know what you're doing."""

    mode: BotModeCfg = BotModeCfg()
    log_level: int = attr.ib(
        default=logging.INFO,
        metadata={
            METADATA_TABLE: ConfigMetadata(
                description="Logging level.",
                hidden=True,
            )
        },
    )

    @log_level.validator
    def _log_level_validator(self, a: attr.Attribute, value: int) -> None:
        """Validate that log_level is within 0 to 50."""
        if value not in range(0, 50 + 1):
            raise ValueError("log_level must be an integer within 0 to 50, inclusive.")


@attr.mutable(slots=True)
class EmojiCfg:
    """
    Emojis used across the entire bot.

    This was a pain to implement.
    """

    success: typing.Any = attr.ib(
        default=":thumbsup:",
        metadata={
            METADATA_TABLE: ConfigMetadata(
                description="This is used in most cases when the bot does a successful action.",
                discord_converter=BetterPartialEmojiConverter,
                discord_converter_attribute=lambda x: x.id or f"{x.name}",
            )
        },
    )

    failure: typing.Any = attr.ib(
        default=":x:",
        metadata={
            METADATA_TABLE: ConfigMetadata(
                description="This is used in most cases when the bot fails an action.",
                discord_converter=BetterPartialEmojiConverter,
                discord_converter_attribute=lambda x: x.id or f"{x.name}",
            )
        },
    )


@attr.s(auto_attribs=True, slots=True)
class Cfg:
    """
    Base configuration attrs class.

    The reason this creates defaults of the variables is so
    we can get a clean default variable if we don't pass anything.
    """

    bot: BotCfg = BotCfg()
    colours: Colours = Colours()
    dev: DevCfg = attr.ib(
        default=DevCfg(),
        metadata={
            METADATA_TABLE: ConfigMetadata(
                description=(
                    "Developer configuration. Only change these values if you know what you're doing."
                ),
                hidden=True,
            )
        },
    )
    emojis: EmojiCfg = EmojiCfg()


# build configuration
ConfigurationSchema = desert.schema_class(Cfg, meta={"ordered": True})  # noqa: N818


_CACHED_CONFIG: "Config" = None
_CACHED_DEFAULT: Cfg = None


@attr.s(auto_attribs=True, slots=True, kw_only=True)
class Config:
    """
    Base configuration variable. Used across the entire bot for configuration variables.

    Holds two variables, default and user.
    Default is a Cfg instance with nothing passed. It is a default instance of Cfg.

    User is a Cfg schema instance, generated from a combination of the defaults,
    user provided toml, and environment variables.
    """

    user: Cfg
    schema: marshmallow.Schema
    default: Cfg = Cfg()


ClassT = typing.TypeVar("ClassT", bound=type)


# find and build a bot class from our env
def _build_class(
    klass: ClassT,
    env: typing.Dict[str, str] = None,
    env_prefix: str = None,
    *,
    dotenv_file: os.PathLike = None,
    defaults: typing.Dict = None,
) -> ClassT:
    """
    Create an instance of the provided klass from env vars prefixed with ENV_PREFIX and class_prefix.

    Defaults to getting the environment variables with dotenv.
    Also can parse from a provided dictionary of environment variables.
    If `defaults` is provided, uses a value from there if the environment variable is not set or is None.
    """
    if env_prefix is None:
        env_prefix = ENV_PREFIX

    if env is None:
        if dotenv_file is not None:
            env = dotenv.dotenv_values(dotenv_file)
            env.update(os.environ)
        else:
            env = os.environ.copy()

    # get the attributes of the provided class
    if defaults is None:
        defaults = defaultdict(lambda: None)
    else:
        defaults = defaultdict(lambda: None, defaults.copy())

    kw = defaultdict(lambda: None)  # any missing required vars provide as missing

    for var in attr.fields(klass):
        if attr.has(var.type):
            # var is an attrs class too
            kw[var.name] = _build_class(
                var.type,
                env=env,
                env_prefix=env_prefix + var.name.upper() + "_",
                defaults=defaults.get(var.name, None),
            )
        else:
            kw[var.name] = env.get(env_prefix + var.name.upper(), None)
            if kw[var.name] is None:
                if (defa := defaults.get(var.name, None)) is not None and defa is not marshmallow.missing:
                    kw[var.name] = defaults[var.name]
                elif var.default is not attr.NOTHING:  # check for var default
                    kw[var.name] = var.default
                else:
                    del kw[var.name]

    return klass(**kw)


def load_env(env_file: os.PathLike = None, existing_cfg_dict: dict = None) -> dict:
    """
    Load a configuration dictionary from the specified env file and environment variables.

    All dependencies for this will always be installed.
    """
    if env_file is None:
        env_file = _CWD / ".env"
    else:
        env_file = pathlib.Path(env_file)

    if not existing_cfg_dict:
        existing_cfg_dict = defaultdict(_generate_default_dict)

    existing_cfg_dict = attr.asdict(_build_class(Cfg, dotenv_file=env_file, defaults=existing_cfg_dict))

    return existing_cfg_dict


def load_toml(path: os.PathLike = None) -> defaultdict:
    """
    Load a configuration dictionary from the specified toml file.

    All dependencies for this will always be installed.
    """
    if path is None:
        path = (_CWD / (USER_CONFIG_FILE_NAME + ".toml"),)
    else:
        # fully resolve path
        path = pathlib.Path(path)

    if not path.is_file():
        raise CfgLoadError("The provided toml file path is not a valid file.")

    try:
        with open(path) as f:
            return defaultdict(lambda: marshmallow.missing, atoml.parse(f.read()).value)
    except Exception as e:
        raise CfgLoadError from e


def load_yaml(path: os.PathLike) -> dict:
    """
    Load a configuration dictionary from the specified yaml file.

    The dependency for this may not be installed, as toml is already used elsewhere, so this is optional.

    In order to keep errors at a minimum, this function checks if both pyyaml is installed
    and if a yaml configuration file exists before raising an exception.
    """
    if path is None:
        path = (_CWD / (USER_CONFIG_FILE_NAME + ".yaml"),)
    else:
        path = pathlib.Path(path)

    states = [
        ("The yaml library is not installed.", yaml is not None),
        ("The provided yaml config path does not exist.", path.exists()),
        ("The provided yaml config file is not a readable file.", path.is_file()),
    ]
    if errors := "\n".join(msg for msg, check in states if not check):
        raise CfgLoadError(errors)

    try:
        with open(path, "r") as f:
            return defaultdict(lambda: marshmallow.missing, yaml.load(f.read(), Loader=yaml.SafeLoader))
    except Exception as e:
        raise CfgLoadError from e


DictT = typing.TypeVar("DictT", bound=typing.Dict[str, typing.Any])


def _remove_extra_values(klass: type, dit: DictT) -> DictT:
    """
    Remove extra values from the provided dict which don't fit into the provided klass recursively.

    klass must be an attr.s class.
    """
    fields = attr.fields_dict(klass)
    cleared_dict = dit.copy()
    for k in dit:
        if k not in fields:
            del cleared_dict[k]
        elif isinstance(cleared_dict[k], dict):
            if attr.has((new_klass := fields.get(k, None)).type):
                cleared_dict[k] = _remove_extra_values(new_klass.type, cleared_dict[k])
            else:
                # delete this dict
                del cleared_dict[k]
    return cleared_dict


def _load_config(*files: os.PathLike, should_load_env: bool = True) -> Config:
    """
    Loads a configuration from the specified files.

    Configuration will stop loading on the first existing file.
    Default order checks yaml, then toml.

    Supported file types are .toml or .yaml
    """

    def raise_missing_dep(file_type: str, dependency: str = None) -> typing.NoReturn:
        raise CfgLoadError(
            f"The required dependency for reading {file_type} configuration files is not installed. "
            f"Please install {dependency or file_type} to allow reading these files."
        )

    if len(files) == 0:
        files = USER_CONFIG_FILES

    loaded_config_dict: dict = None
    for file in files:
        if not isinstance(file, pathlib.Path):
            file = pathlib.Path(file)
        if not file.exists():
            # file does not exist
            continue

        if file.suffix == ".toml":
            if atoml is None:
                raise_missing_dep("toml", "atoml")
            loaded_config_dict = load_toml(file)
            break
        elif file.suffix == ".yaml":
            if yaml is None:
                raise_missing_dep("yaml", "pyyaml")
            loaded_config_dict = load_yaml(file)
            break
        else:
            raise CfgLoadError("Provided configuration file is not of a supported type.")

    if should_load_env:
        loaded_config_dict = load_env(existing_cfg_dict=loaded_config_dict)

    # HACK remove extra keeps from the configuration dict since marshmallow doesn't know what to do with them
    # CONTRARY to the marshmallow.EXCLUDE below.
    # They will cause errors.
    # Extra configuration values are okay, we aren't trying to be strict here.
    loaded_config_dict = _remove_extra_values(Cfg, loaded_config_dict)

    loaded_config_dict = ConfigurationSchema().load(data=loaded_config_dict, unknown=marshmallow.EXCLUDE)
    return Config(user=loaded_config_dict, schema=ConfigurationSchema, default=get_default_config())


def get_config() -> Config:
    """
    Helps to try to ensure that only one instance of the Config class exists.

    This means that all usage of the configuration is using the same configuration class.
    """
    global _CACHED_CONFIG
    if _CACHED_CONFIG is None:
        _CACHED_CONFIG = _load_config()
    return _CACHED_CONFIG


def get_default_config() -> Cfg:
    """Get the default configuration instance of the global Config instance."""
    global _CACHED_DEFAULT
    if _CACHED_DEFAULT is None:
        _CACHED_DEFAULT = Cfg()
    return _CACHED_DEFAULT


config = get_config
default = get_default_config
