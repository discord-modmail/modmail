import logging
import operator
import string
import typing

import attr
import attr._make
import marshmallow
from discord.ext import commands
from discord.ext.commands import Context

from modmail import config
from modmail.bot import ModmailBot
from modmail.log import ModmailLogger
from modmail.utils.cogs import ExtMetadata, ModmailCog
from modmail.utils.pagination import ButtonPaginator


EXT_METADATA = ExtMetadata()

logger: ModmailLogger = logging.getLogger(__name__)


@attr.mutable
class ConfOptions:
    """Configuration attribute class."""

    default: str
    name: str
    description: str
    canconical_name: str
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
        """Create a ConfOptions from a attr.Attribute."""
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
        kw["canconical_name"] = meta.canconical_name
        kw["extended_description"] = meta.extended_description
        kw["hidden"] = meta.hidden

        if nested is not None:
            kw["nested"] = nested

        return cls(**kw)


def get_all_conf_options(klass: config.ClassT, *, prefix: str = None) -> typing.Dict[str, ConfOptions]:
    """Get a dict of ConfOptions for a designated configuration field recursively."""
    options = dict()
    for field in attr.fields(klass):
        # make conf option list
        if attr.has(field.type):
            options.update(get_all_conf_options(field.type, prefix=field.name + "."))
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
        for table, opt in self.config_fields.items():
            if opt.hidden or opt.frozen:
                continue

            # we want to merge items from the same config table so they are on the same table
            key = table.rsplit(".", 1)[0]
            options[key] = options.get(key, "") + (
                "\n".join(
                    [
                        f"**{string.capwords(opt.canconical_name or opt.name)}**",
                        f"Default: `{opt.default}`"
                        if opt.default is not None
                        else "Required. There is no default value for this option.",
                        f"{opt.description}",
                        f" {opt.extended_description}\n" if opt.extended_description else "",
                    ]
                )
            )

        await ButtonPaginator.paginate(options.values(), ctx.message)

    @config_group.command(name="set", aliases=("edit",))
    async def modify_config(self, ctx: Context, option: str, value: str) -> None:
        """Modify an existing configuration value."""
        if option not in self.config_fields:
            raise commands.BadArgument(f"Option must be in {', '.join(self.config_fields.keys())}")
        meta = self.config_fields[option]

        if meta.frozen:
            await ctx.send("Can't modify this value.")
            return

        if meta.modmail_metadata.discord_converter is not None:
            value = await meta.modmail_metadata.discord_converter().convert(ctx, value)
        elif meta._field.converter:
            value = meta._field.converter(value)
        get_value = operator.attrgetter(option.rsplit(".", -1)[0])
        setattr(get_value(self.bot.config.user), option.rsplit(".", -1)[-1], value)
        await ctx.message.reply("ok.")

    @config_group.command(name="get", aliases=("show",))
    async def get_config(self, ctx: Context, option: str) -> None:
        """Modify an existing configuration value."""
        if option not in self.config_fields:
            raise commands.BadArgument(f"Option must be in {', '.join(self.config_fields.keys())}")

        get_value = operator.attrgetter(option)
        value = get_value(self.bot.config.user)
        await ctx.send(f"{option}: `{value}`")


def setup(bot: ModmailBot) -> None:
    """Load the ConfigurationManager cog."""
    bot.add_cog(ConfigurationManager(bot))
