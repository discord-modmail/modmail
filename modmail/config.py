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


_CWD = pathlib.Path(os.getcwd())
ENV_PREFIX = "MODMAIL_"
USER_CONFIG_TOML = _CWD / "modmail_config.toml"

env = environs.Env(eager=False, expand_vars=True)
env.read_env(_CWD / ".env", recurse=False)


def _generate_default_dict() -> defaultdict:
    """For defaultdicts to default to a defaultdict."""
    return defaultdict(_generate_default_dict)


unparsed_user_provided_cfg = defaultdict(lambda: marshmallow.missing)
try:
    with open(USER_CONFIG_TOML) as f:
        unparsed_user_provided_cfg.update(atoml.parse(f.read()).value)
except FileNotFoundError:
    pass


class _ColourField(marshmallow.fields.Field):
    """Class to convert a str or int into a color and deseriaze into a string."""

    class ColourConvert(discord.ext.commands.converter.ColourConverter):
        def convert(self, argument: str) -> discord.Colour:
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

    def _serialize(self, value: typing.Any, attr: str, obj: typing.Any, **kwargs) -> discord.Colour:
        return str(value.value)

    def _deserialize(
        self,
        value: typing.Any,
        attr: typing.Optional[str],
        data: typing.Optional[typing.Mapping[str, typing.Any]],
        **kwargs,
    ) -> str:
        if not isinstance(value, discord.Colour):
            if isinstance(value, str):
                value = self.ColourConvert().convert(value)
            else:
                value = discord.Colour(value)
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
        if value not in range(0, 50):
            raise ValueError("log_level must be an integer within 0 to 50.")


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


# find and build a bot class from our env
def _build_bot_class(klass: typing.Any, class_prefix: str = "", defaults: typing.Dict = None) -> Bot:
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


_toml_bot_cfg = unparsed_user_provided_cfg["bot"]
unparsed_user_provided_cfg["bot"] = attr.asdict(
    _build_bot_class(Bot, "BOT_", _toml_bot_cfg if _toml_bot_cfg is not marshmallow.missing else None)
)
del _toml_bot_cfg
# build configuration
Configuration = desert.schema_class(Cfg, meta={"ordered": True})  # noqa: N818
USER_PROVIDED_CONFIG: Cfg = Configuration().load(unparsed_user_provided_cfg, unknown=marshmallow.EXCLUDE)
DEFAULTS_CONFIG = Cfg()


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
    default: Cfg
    schema: marshmallow.Schema


config = Config(user=USER_PROVIDED_CONFIG, default=DEFAULTS_CONFIG, schema=Configuration)
