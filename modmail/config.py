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
    "export_default_conf",
    "get_config",
    "get_default_config",
    "load_toml",
    "load_yaml",
]

_CWD = pathlib.Path.cwd()

ENV_PREFIX = "MODMAIL_"
USER_CONFIG_FILE_NAME = "modmail_config"
AUTO_GEN_FILE_NAME = "default_config"
DEFAULT_CONFIG_FILES = [
    _CWD / (USER_CONFIG_FILE_NAME + ".yaml"),
    _CWD / (USER_CONFIG_FILE_NAME + ".toml"),
]


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
        },
    )
    prefix: str = attr.ib(
        default="?",
        converter=lambda x: "?" if x is None else x,
        metadata={
            "allow_none": False,
        },
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
    attribs: typing.Set[attr.Attribute] = set()
    for a in dir(klass.__attrs_attrs__):
        if hasattr(klass.__attrs_attrs__, a):
            if isinstance(attribute := getattr(klass.__attrs_attrs__, a), attr.Attribute):
                attribs.add(attribute)
    # read the env vars from the above
    with env.prefixed(ENV_PREFIX):
        kw = defaultdict(lambda: marshmallow.missing)  # any missing required vars provide as missing
        for var in attribs:
            kw[var.name] = getattr(env, var.type.__name__)(class_prefix + var.name.upper())
            if defaults and kw[var.name] is None:
                kw[var.name] = defaults[var.name]

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

    existing_cfg_dict["bot"].update(attr.asdict(_build_bot_class(Bot, env, "BOT_")))

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
                loaded_cfg.update(existing_cfg_dict)
                return existing_cfg_dict
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


def _load_config(files: typing.List[typing.Union[os.PathLike]] = None, load_env: bool = True) -> Config:
    """
    Loads a configuration from the specified files.

    Configuration will stop loading on the first existing file.
    Default order checks yaml, then toml.

    Supported file types are .toml or .yaml
    """
    # load the env first
    if load_env:
        env_cfg = _load_env()
    else:
        env_cfg = None

    if files is None:
        files = DEFAULT_CONFIG_FILES
    elif len(files) == 0:
        raise CfgLoadError("At least one file to load from must be provided.")

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

    if loaded_config_dict is None:
        raise CfgLoadError(
            "Not gonna lie, this SHOULD be unreachable...\n"
            "If you came across this as a consumer, please report this bug to our bug tracker."
        )
    loaded_config_dict = ConfigurationSchema().load(loaded_config_dict)
    return Config(user=loaded_config_dict, schema=ConfigurationSchema)


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
    return get_config().default


def export_default_conf(*, export_toml: bool = True, export_yaml: bool = None) -> bool:
    """Export default configuration to the preconfigured locations."""
    conf = get_default_config()
    dump: dict = ConfigurationSchema().dump(conf)

    # Sort the dictionary configuration.
    # This is the only place where the order of the config should matter, when exporting in a specific style
    def sort_dict(d: dict) -> dict:
        """Takes a dict and sorts it, recursively."""
        sorted_dict = {x[0]: x[1] for x in sorted(d.items(), key=lambda e: e[0])}

        for k, v in d.items():
            if not isinstance(v, dict):
                continue
            sorted_dict[k] = sort_dict(v)

        return sorted_dict

    dump = sort_dict(dump)

    doc = atoml.document()
    doc.add(atoml.comment("This is an autogenerated TOML document."))
    doc.add(atoml.comment("Directly run the config.py file to generate."))
    doc.add(atoml.nl())

    doc.update(dump)

    # toml
    if export_toml:
        with open(pathlib.Path(__file__).parent / (AUTO_GEN_FILE_NAME + ".toml"), "w") as f:
            atoml.dump(doc, f)

    # yaml
    if export_yaml is True or (yaml is not None and export_yaml is None):
        with open(pathlib.Path(__file__).parent / (AUTO_GEN_FILE_NAME + ".yaml"), "w") as f:
            try:
                yaml.dump(dump, f, indent=4, Dumper=yaml.SafeDumper)
            except AttributeError:
                raise CfgLoadError(
                    "Tried to export the yaml configuration file but pyyaml is not installed."
                ) from None


config = get_config()
