import logging
import operator
import string
import types
import typing

import attr
import attr._make
import discord
import marshmallow
from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands import converter as commands_converter

from modmail import config
from modmail.bot import ModmailBot
from modmail.log import ModmailLogger
from modmail.utils import responses
from modmail.utils.cogs import ExtMetadata, ModmailCog
from modmail.utils.pagination import ButtonPaginator


EXT_METADATA = ExtMetadata()

logger: ModmailLogger = logging.getLogger(__name__)

KeyT = str


@attr.mutable
class ConfOptions:
    """Configuration attribute class."""

    default: str
    name: str
    description: str
    canonical_name: str
    extended_description: str
    hidden: bool

    _type: type

    metadata: dict

    modmail_metadata: config.ConfigMetadata

    _field: attr.Attribute = None
    nested: str = None
    frozen: bool = False

    @classmethod
    def from_field(cls, field: attr.Attribute, *, frozen: bool = False, nested: str = None):
        """Create a ConfOptions from an attr.Attribute."""
        kw = {}
        kw["default"] = field.default if field.default is not marshmallow.missing else None
        kw["name"] = field.name
        kw["type"] = field.type

        kw["metadata"] = field.metadata
        kw["field"] = field

        kw["frozen"] = field.on_setattr is attr.setters.frozen or frozen

        meta: config.ConfigMetadata = field.metadata[config.METADATA_TABLE]
        kw[config.METADATA_TABLE] = meta
        kw["description"] = meta.description
        kw["canonical_name"] = meta.canonical_name
        kw["extended_description"] = meta.extended_description
        kw["hidden"] = meta.hidden

        if nested is not None:
            kw["nested"] = nested

        return cls(**kw)


def get_all_conf_options(klass: config.ClassT, *, prefix: str = "") -> typing.Dict[str, ConfOptions]:
    """Get a dict of ConfOptions for a designated configuration field recursively."""
    options = dict()
    for field in attr.fields(klass):
        # make conf option list
        if attr.has(field.type):
            options.update(get_all_conf_options(field.type, prefix=prefix + field.name + "."))
        else:
            is_frozen = klass.__setattr__ is attr._make._frozen_setattrs
            try:
                conf_opt = ConfOptions.from_field(field, frozen=is_frozen, nested=prefix)
            except KeyError as e:
                if field.type == type:
                    pass
                elif config.METADATA_TABLE in e.args[0]:
                    logger.warn(
                        f"Issue with field '{field.name}', does not have a {config.METADATA_TABLE} key."
                    )
                else:
                    logger.error(f"A key error occured with {field.name}.", exc_info=True)
            else:
                options[prefix + field.name] = conf_opt

    return options


class KeyConverter(commands.Converter):
    """Convert argument into a configuration key."""

    async def convert(self, ctx: Context, arg: str) -> KeyT:
        """Ensure that a key is of the valid format, allowing a user to input other formats."""
        # basically we're converting an argument to a key.
        # config keys are delimited by `.`, and always lowercase, which means that we can make a few passes
        # before actually trying to make any guesses.
        # the problems are twofold. a: we want to suggest other keys
        # and b: the interface needs to be easy to use.

        # as a partial solution for this, `/`, `-`, `.` are all valid delimiters and are converted to `.`
        # depending on common problems, it is *possible* to add `_` but would require fuzzy matching over
        # all of the keys since that can also be a valid character name.

        fields = get_all_conf_options(config.default().__class__)

        new_arg = ""
        for c in arg.lower():
            if c in " /`":
                new_arg += "."
            else:
                new_arg += c

        if new_arg in fields:
            return new_arg
        else:
            raise commands.BadArgument(
                f"{ctx.current_parameter.name.capitalize()} `{arg}` is not a valid configuration key."
            )


class ConfigurationManager(ModmailCog, name="Configuration Manager"):
    """Manage the bot configuration."""

    config_fields: typing.Dict[str, ConfOptions]

    def __init__(self, bot: ModmailBot):
        self.bot = bot

        self.config_fields = get_all_conf_options(config.default().__class__)

    @commands.group(name="config", aliases=("cfg", "conf"), invoke_without_command=True)
    async def config_group(self, ctx: Context) -> None:
        """Manage the bot configuration."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @config_group.command(name="list")
    async def list_config(self, ctx: Context) -> None:
        """List the valid configuration options."""
        options = {}

        embed = discord.Embed(title="Configuration Options")
        for table, opt in self.config_fields.items():
            # TODO: add flag to skip this check
            if opt.hidden or opt.frozen:
                # bot refuses to modify a hidden value
                # and bot cannot modify a frozen value
                continue

            # we want to merge items from the same config table so they display on the same pagination page
            # for example, all emoji configuration options will not be split up
            key = table.rsplit(".", 1)[0]
            if options.get(key) is None:
                options[key] = f"**__{string.capwords(key)} config__**\n"

            name = opt.canonical_name or opt.name
            default = f"Default: `{opt.default}`" if opt.default is not None else "Required."
            description = opt.description
            if opt.extended_description:
                description += "\n" + opt.extended_description

            options[key] += "\n".join([f"**{name}**", default, description]).strip() + "\n"

        await ButtonPaginator.paginate(options.values(), ctx.message, embed=embed)

    @config_group.command(name="set", aliases=("edit",))
    async def modify_config(self, ctx: Context, option: KeyConverter, value: str) -> None:
        """Modify an existing configuration value."""
        if option not in self.config_fields:
            raise commands.BadArgument(f"Option must be in {', '.join(self.config_fields.keys())}")
        meta = self.config_fields[option]

        if meta.frozen:

            await responses.send_negatory_response(ctx, f"Unable to modify {option}.")
            return

        if meta.modmail_metadata.discord_converter is not None:
            value = await meta.modmail_metadata.discord_converter().convert(ctx, value)
            if meta.modmail_metadata.discord_converter_attribute is not None:
                if isinstance(meta.modmail_metadata.discord_converter_attribute, types.FunctionType):
                    value = meta.modmail_metadata.discord_converter_attribute(value)
        if meta._type in commands_converter.CONVERTER_MAPPING:
            value = await commands_converter.CONVERTER_MAPPING[meta._type]().convert(ctx, value)
            if isinstance(meta.modmail_metadata.discord_converter_attribute, types.FunctionType):
                value = meta.modmail_metadata.discord_converter_attribute(value)
        elif meta._field.converter:
            value = meta._field.converter(value)

        if "." in option:
            root, name = option.rsplit(".", -1)
        else:
            root = ""
            name = option

        setattr(operator.attrgetter(root)(self.bot.config.user), name, value)

        await responses.send_positive_response(ctx, f"Successfully set `{option}` to `{value}`.")

    @config_group.command(name="get", aliases=("show",))
    async def get_config(self, ctx: Context, option: KeyConverter) -> None:
        """Modify an existing configuration value."""
        if option not in self.config_fields:
            raise commands.BadArgument(f"Option must be in {', '.join(self.config_fields.keys())}")

        get_value = operator.attrgetter(option)
        value = get_value(self.bot.config.user)
        await ctx.send(f"{option}: `{value}`")


def setup(bot: ModmailBot) -> None:
    """Load the ConfigurationManager cog."""
    bot.add_cog(ConfigurationManager(bot))
