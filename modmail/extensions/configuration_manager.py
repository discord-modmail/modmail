import logging
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

    nested: str = None
    frozen: bool = False

    @classmethod
    def from_field(cls, field: attr.Attribute, *, frozen: bool = False, nested: str = None):
        """Create a ConfOptions from a attr.Attribute."""
        kw = {}
        kw["default"] = field.default if field.default is not marshmallow.missing else None
        kw["name"] = field.name
        kw["type"] = field.type

        kw["frozen"] = field.on_setattr is attr.setters.frozen or frozen

        meta: config.ConfigMetadata = field.metadata[config.METADATA_TABLE]
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


def setup(bot: ModmailBot) -> None:
    """Load the ConfigurationManager cog."""
    bot.add_cog(ConfigurationManager(bot))
