import inspect
import logging
import os
import pathlib
import typing
from collections import defaultdict

import atoml
import attr
import desert
import discord
import discord.ext.commands.converter
import environs
import marshmallow
import marshmallow.fields
import marshmallow.validate


try:
    import yaml
except ImportError:
    yaml = None

__all__ = [
    "AUTO_GEN_FILE_NAME",
    "DEFAULT_CONFIG_FILES",
    "ENV_PREFIX",
    "BOT_ENV_PREFIX",
    "USER_CONFIG_FILE_NAME",
    "CfgLoadError",
    "Config",
    "config",
    "ConfigurationSchema",
    "Bot",
    "BotModeCfg",
    "Cfg",
    "Colours",
    "DevCfg",
    "convert_to_color",
    "get_config",
    "get_default_config",
    "load_toml",
    "load_yaml",
]

_CWD = pathlib.Path.cwd()

ENV_PREFIX = "MODMAIL_"
BOT_ENV_PREFIX = "BOT_"
USER_CONFIG_FILE_NAME = "modmail_config"
AUTO_GEN_FILE_NAME = "default_config"
DEFAULT_CONFIG_FILES = [
    _CWD / (USER_CONFIG_FILE_NAME + ".yaml"),
    _CWD / (USER_CONFIG_FILE_NAME + ".toml"),
]


def _generate_default_dict() -> defaultdict:
    """For defaultdicts to default to a defaultdict."""
    return defaultdict(_generate_default_dict)


def _recursive_dict_update(d1: dict, d2: dict) -> defaultdict:
    """
    Recursively update a dictionary with the values from another dictionary.

    Serves to ensure that all keys from both exist.
    """
    d1.update(d2)
    for k, v in d1.items():
        if isinstance(v, dict) and isinstance(d2.get(k, None), dict):
            d1[k] = _recursive_dict_update(v, d2[k])
        elif v is marshmallow.missing and d2.get(k, marshmallow.missing) is not marshmallow.missing:
            d1[k] = d2[k]
    return defaultdict(lambda: marshmallow.missing, d1)


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

    def _serialize(self, value: discord.Colour, attr: str, obj: typing.Any, **kwargs) -> discord.Colour:
        return "#" + hex(value.value)[2:].lower()

    def _deserialize(
        self,
        value: typing.Any,
        attr: typing.Optional[str],
        data: typing.Optional[typing.Mapping[str, typing.Any]],
        **kwargs,
    ) -> str:
        if not isinstance(value, discord.Colour):
            value = self.ColourConvert().convert(value)
        return value


def convert_to_color(col: typing.Union[str, int, discord.Colour]) -> discord.Colour:
    """Convert a string or integer to a discord.Colour. Also supports being passed a discord.Colour."""
    return _ColourField.ColourConvert().convert(col)


@attr.s(auto_attribs=True, slots=True)
class Bot:
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
            "modmail_export_filler": "MyBotToken",
            "modmail_env_description": "Discord bot token. This is obtainable from https://discord.com/developers/applications",  # noqa: E501
        },
    )
    prefix: str = attr.ib(
        default=marshmallow.missing,
        converter=lambda x: "?" if x is marshmallow.missing else x,
    )


@attr.s(auto_attribs=True, slots=True, frozen=True)
class BotModeCfg:
    """
    The three bot modes for the bot. Enabling some of these may enable other bot features.

    `production` is used internally and is always True.
    `develop` enables additonal features which are useful for bot developers.
    `plugin_dev` enables additional commands which are useful when working with plugins.
    """

    production: bool = desert.ib(
        marshmallow.fields.Constant(True),
        default=True,
        converter=lambda _: True,
        metadata={"dump_default": True, "dump_only": True},
    )
    develop: bool = attr.ib(default=False, metadata={"allow_none": False})
    plugin_dev: bool = attr.ib(default=False, metadata={"allow_none": False})


@attr.s(auto_attribs=True, slots=True)
class Colours:
    """
    Default colors.

    These should only be changed here to change the default colors.
    """

    base_embed_color: discord.Colour = desert.ib(
        _ColourField(), default="0x7289DA", converter=convert_to_color
    )


@attr.s(auto_attribs=True, slots=True)
class DevCfg:
    """Developer configuration. These values should not be changed unless you know what you're doing."""

    mode: BotModeCfg = BotModeCfg()
    log_level: int = attr.ib(default=logging.INFO)

    @log_level.validator
    def _log_level_validator(self, _: attr.Attribute, value: int) -> None:
        """Validate that log_level is within 0 to 50."""
        if value not in range(0, 50 + 1):
            raise ValueError("log_level must be an integer within 0 to 50, inclusive.")


@attr.s(auto_attribs=True, slots=True)
class Cfg:
    """
    Base configuration attrs class.

    The reason this creates defaults of the variables is so
    we can get a clean default variable if we don't pass anything.
    """

    bot: Bot = Bot()
    colours: Colours = Colours()
    dev: DevCfg = DevCfg()


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


# find and build a bot class from our env
def _build_bot_class(
    klass: typing.Any, env: environs.Env, class_prefix: str = "", defaults: typing.Dict = None
) -> Bot:
    """
    Create an instance of the provided klass from env vars prefixed with ENV_PREFIX and class_prefix.

    If defaults is provided, uses a value from there if the environment variable is not set or is None.
    """
    # get the attributes of the provided class
    if defaults is None:
        defaults = defaultdict(lambda: marshmallow.missing)
    else:
        defaults = defaultdict(lambda: marshmallow.missing, defaults.copy())

    with env.prefixed(ENV_PREFIX):
        kw = defaultdict(lambda: marshmallow.missing)  # any missing required vars provide as missing
        for var in attr.fields(klass):
            kw[var.name] = getattr(env, var.type.__name__)(class_prefix + var.name.upper())
            if defaults and kw[var.name] is None:
                kw[var.name] = defaults[var.name]
            elif kw[var.name] is None:
                kw[var.name] = marshmallow.missing

    return klass(**kw)


def _load_env(env_file: os.PathLike = None, existing_cfg_dict: dict = None) -> dict:
    """
    Load a configuration dictionary from the specified env file and environment variables.

    All dependencies for this will always be installed.
    """
    if env_file is None:
        env_file = _CWD / ".env"
    else:
        env_file = pathlib.Path(env_file)

    env = environs.Env(eager=False, expand_vars=True)
    env.read_env(".env", recurse=False)

    if not existing_cfg_dict:
        existing_cfg_dict = defaultdict(_generate_default_dict)

    existing_cfg_dict["bot"] = _recursive_dict_update(
        existing_cfg_dict["bot"], attr.asdict(_build_bot_class(Bot, env, BOT_ENV_PREFIX))
    )

    return existing_cfg_dict


def load_toml(path: os.PathLike = None, existing_cfg_dict: dict = None) -> defaultdict:
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
            loaded_cfg = defaultdict(lambda: marshmallow.missing, atoml.parse(f.read()).value)
            if existing_cfg_dict is not None:
                _recursive_dict_update(loaded_cfg, existing_cfg_dict)
                return loaded_cfg
            else:
                return loaded_cfg
    except Exception as e:
        raise CfgLoadError from e


def load_yaml(path: os.PathLike, existing_cfg_dict: dict = None) -> dict:
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
            loaded_cfg = dict(yaml.load(f.read(), Loader=yaml.SafeLoader))
            if existing_cfg_dict is not None:
                loaded_cfg.update(existing_cfg_dict)
                return existing_cfg_dict
            else:
                return loaded_cfg
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


def _load_config(*files: os.PathLike, load_env: bool = True) -> Config:
    """
    Loads a configuration from the specified files.

    Configuration will stop loading on the first existing file.
    Default order checks yaml, then toml.

    Supported file types are .toml or .yaml
    """
    env_cfg = None

    if len(files) == 0:
        files = DEFAULT_CONFIG_FILES

    loaded_config_dict: dict = None
    for file in files:
        if not isinstance(file, pathlib.Path):
            file = pathlib.Path(file)
        if not file.exists():
            # file does not exist
            continue

        if file.suffix == ".toml" and atoml is not None:
            loaded_config_dict = load_toml(file, existing_cfg_dict=env_cfg)
            break
        elif file.suffix == ".yaml" and yaml is not None:
            loaded_config_dict = load_yaml(file, existing_cfg_dict=env_cfg)
            break
        else:
            raise Exception(
                "Provided configuration file is not of a supported type or "
                "the required dependencies are not installed."
            )

    if load_env:
        loaded_config_dict = _load_env(existing_cfg_dict=loaded_config_dict)

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
