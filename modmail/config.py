import inspect
import logging
import os
import pathlib
import sys
import typing
from collections import defaultdict
from pprint import pprint

import atoml
import attr
import desert
import discord
import environs
import marshmallow
import marshmallow.fields
import marshmallow.validate


ENV_PREFIX = "MODMAIL_"

env = environs.Env(eager=False, expand_vars=True)


DEFAULT_CONFIG_PATH = pathlib.Path(os.path.join(os.path.dirname(__file__), "test.toml"))


def _generate_default_dict():
    """For defaultdicts to default to a defaultdict."""
    return defaultdict(_generate_default_dict)


try:
    with open(DEFAULT_CONFIG_PATH) as f:
        unparsed_user_provided_cfg = defaultdict(_generate_default_dict, atoml.parse(f.read()).value)
except FileNotFoundError:
    unparsed_user_provided_cfg = defaultdict(_generate_default_dict)


class _ColourField(marshmallow.fields.Field):
    """Class to convert a str or int into a color and deseriaze into a string."""

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
            value = discord.Colour(int(value, 16))
        return value


# marshmallow.fields.Colour = _ColourField


@attr.s(auto_attribs=True, frozen=True)
class Bot:
    """Values that are configuration for the bot itself.

    These are metavalues, and are the token, prefix, database bind, basically all of the stuff that needs to
    be known BEFORE attempting to log in to the database or discord.
    """

    token: str = attr.ib(
        default=marshmallow.missing,
        metadata={
            "required": True,
            "load_only": True,
            "allow_none": False,
        },
    )
    prefix: str = attr.ib(
        default="?",
        metadata={
            "allow_none": False,
        },
    )

    class Meta:
        load_only = ("token",)
        partial = True


def convert_to_color(col: typing.Union[str, int, discord.Colour]) -> discord.Colour:
    if isinstance(col, discord.Colour):
        return col
    if isinstance(col, str):
        col = int(col, 16)
    return discord.Colour(col)


@attr.s(auto_attribs=True)
class BotModeCfg:
    production: bool = desert.ib(
        marshmallow.fields.Constant(True), default=True, metadata={"dump_default": True, "dump_only": True}
    )
    develop: bool = attr.ib(default=False, metadata={"allow_none": False})
    plugin_dev: bool = attr.ib(default=False, metadata={"allow_none": False})


@attr.s(auto_attribs=True)
class Colours:
    """
    Default colors.

    These should only be changed here to change the default colors.
    """

    base_embed_color: discord.Colour = desert.ib(
        _ColourField(), default="0x7289DA", converter=convert_to_color
    )


@attr.s(auto_attribs=True)
class DevCfg:
    mode: BotModeCfg = BotModeCfg()
    log_level: int = desert.ib(
        marshmallow.fields.Integer(
            validate=marshmallow.validate.Range(0, 50, error="Logging level must be within 0 to 50.")
        ),
        default=logging.INFO,
    )


@attr.s(auto_attribs=True)
class Cfg:
    bot: Bot = Bot()
    colours: Colours = Colours()
    dev: DevCfg = DevCfg()

    class Meta:
        exclude = ("bot.token",)


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


unparsed_user_provided_cfg["bot"] = attr.asdict(
    _build_bot_class(Bot, "BOT_", unparsed_user_provided_cfg["bot"])
)

# env.seal()

# build configuration
Configuration = desert.schema_class(Cfg)  # noqa: N818
USER_PROVIDED_CONFIG: Cfg = Configuration().load(unparsed_user_provided_cfg, unknown=marshmallow.RAISE)


# hide the bot token from serilzation
# this prevents the token from being saved to places.


DEFAULTS_CONFIG = Cfg()


@attr.s(auto_attribs=True, slots=True)
class Config:
    user: Cfg
    default: Cfg


config = Config(USER_PROVIDED_CONFIG, DEFAULTS_CONFIG)

print(config.user.bot.prefix)
