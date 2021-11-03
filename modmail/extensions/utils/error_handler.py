import logging
import re
import typing

import discord
import discord.errors
from discord.ext import commands

from modmail.bot import ModmailBot
from modmail.log import ModmailLogger
from modmail.utils import responses
from modmail.utils.cogs import BotModes, ExtMetadata, ModmailCog
from modmail.utils.extensions import BOT_MODE


logger: ModmailLogger = logging.getLogger(__name__)

EXT_METADATA = ExtMetadata()

ERROR_COLOUR = responses.DEFAULT_FAILURE_COLOUR

ERROR_TITLE_REGEX = re.compile(r"((?<=[a-z])[A-Z]|(?<=[a-zA-Z])[A-Z](?=[a-z]))")

ANY_DEV_MODE = BOT_MODE & (BotModes.DEVELOP.value + BotModes.PLUGIN_DEV.value)


class ErrorHandler(ModmailCog, name="Error Handler"):
    """Handles all errors across the bot."""

    def __init__(self, bot: ModmailBot):
        self.bot = bot

    @staticmethod
    def error_embed(title: str, message: str) -> discord.Embed:
        """Create an error embed with an error colour and reason and return it."""
        return discord.Embed(title=title, description=message, colour=ERROR_COLOUR)

    @staticmethod
    def get_title_from_name(error: typing.Union[Exception, str]) -> str:
        """
        Return a message dervived from the exception class name.

        Eg NSFWChannelRequired returns NSFW Channel Required
        """
        if not isinstance(error, str):
            error = error.__class__.__name__
        return re.sub(ERROR_TITLE_REGEX, r" \1", error)

    @staticmethod
    def _reset_command_cooldown(ctx: commands.Context) -> bool:
        if return_value := ctx.command.is_on_cooldown(ctx):
            ctx.command.reset_cooldown(ctx)
        return return_value

    async def handle_user_input_error(
        self,
        ctx: commands.Context,
        error: commands.UserInputError,
        reset_cooldown: bool = True,
    ) -> discord.Embed:
        """Handling deferred from main error handler to handle UserInputErrors."""
        if reset_cooldown:
            self._reset_command_cooldown(ctx)
        msg = None
        if isinstance(error, commands.BadUnionArgument):
            msg = self.get_title_from_name(str(error))
        title = self.get_title_from_name(error)
        return self.error_embed(title, msg or str(error))

    async def handle_bot_missing_perms(
        self, ctx: commands.Context, error: commands.BotMissingPermissions
    ) -> bool:
        """Handles bot missing permissing by dming the user if they have a permission which may be able to fix this."""  # noqa: E501
        embed = self.error_embed("Permissions Failure", str(error))
        bot_perms = ctx.channel.permissions_for(ctx.me)
        not_responded = True
        if bot_perms >= discord.Permissions(send_messages=True, embed_links=True):
            await ctx.send(embeds=[embed])
            not_responded = False
        elif bot_perms >= discord.Permissions(send_messages=True):
            # make a message as similar to the embed, using as few permissions as possible
            # this is the only place we send a standard message instead of an embed
            # so no helper methods are necessary
            await ctx.send(
                "**Permissions Failure**\n\n"
                "I am missing the permissions required to properly execute your command."
            )
            # intentionally not setting responded to True, since we want to attempt to dm the user
            logger.warning(
                f"Missing partial required permissions for {ctx.channel}. "
                "I am able to send messages, but not embeds."
            )
        else:
            logger.error(f"Unable to send an error message to channel {ctx.channel}")

        if not_responded and ANY_DEV_MODE:
            # non-general permissions
            perms = discord.Permissions(
                administrator=True,
                manage_threads=True,
                manage_roles=True,
                manage_channels=True,
            )
            if perms.value & ctx.channel.permissions_for(ctx.author).value:
                logger.info(
                    f"Attempting to dm {ctx.author} since they have a permission which may be able "
                    "to give the bot send message permissions."
                )
                try:
                    await ctx.author.send(embeds=[embed])
                except discord.Forbidden:
                    logger.notice("Also encountered an error when trying to reply in dms.")
                    return False
            return True

    async def handle_check_failure(
        self, ctx: commands.Context, error: commands.CheckFailure
    ) -> typing.Optional[discord.Embed]:
        """Handle CheckFailures seperately given that there are many of them."""
        title = "Check Failure"
        if isinstance(error, commands.CheckAnyFailure):
            title = self.get_title_from_name(error.checks[-1])
        elif isinstance(error, commands.PrivateMessageOnly):
            title = "DMs Only"
        elif isinstance(error, commands.NoPrivateMessage):
            title = "Server Only"
        elif isinstance(error, commands.BotMissingPermissions):
            # defer handling BotMissingPermissions to a method
            # the error could be that the bot is unable to send messages, which would cause
            # the error handling to fail
            await self.handle_bot_missing_perms(ctx, error)
            return None
        else:
            title = self.get_title_from_name(error)
        embed = self.error_embed(title, str(error))
        return embed

    @ModmailCog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Activates when a command raises an error."""
        if getattr(error, "handled", False):
            logging.debug(f"Command {ctx.command} had its error already handled locally, ignoring.")
            return

        if isinstance(error, commands.CommandNotFound):
            # ignore every time the user inputs a message that starts with our prefix but isn't a command
            # this will be modified in the future to support prefilled commands
            if ANY_DEV_MODE:
                logger.trace(error)
            return

        logger.trace(error)

        embed: typing.Optional[discord.Embed] = None
        should_respond = True

        if isinstance(error, commands.UserInputError):
            embed = await self.handle_user_input_error(ctx, error)
        elif isinstance(error, commands.CheckFailure):
            embed = await self.handle_check_failure(ctx, error)
            # handle_check_failure may send its own error if its a BotMissingPermissions error.
            if embed is None:
                should_respond = False
        elif isinstance(error, commands.ConversionError):
            pass
        elif isinstance(error, commands.DisabledCommand):
            logger.debug("")
            if ctx.command.hidden:
                should_respond = False
            else:
                msg = f"Command `{ctx.invoked_with}` is disabled."
                if reason := ctx.command.extras.get("disabled_reason", None):
                    msg += f"\nReason: {reason}"
                embed = self.error_embed("Command Disabled", msg)

        elif isinstance(error, commands.CommandInvokeError):
            if isinstance(error.original, discord.Forbidden):
                logger.warn(f"Permissions error occurred in {ctx.command}.")
                await self.handle_bot_missing_perms(ctx, error.original)
                should_respond = False
            else:
                # todo: this should properly handle plugin errors and note that they are not bot bugs
                # todo: this should log somewhere else since this is a bot bug.
                # generic error
                logger.error(f'Error occurred in command "{ctx.command}".', exc_info=error.original)
                if ctx.command.cog.__module__.startswith("modmail.plugins"):
                    # plugin msg
                    title = "Plugin Internal Error Occurred"
                    msg = (
                        "Something went wrong internally in the plugin contributed command you were trying "
                        "to execute. Please report this error and what you were trying to do to the "
                        "respective plugin developers.\n\n**PLEASE NOTE**: Modmail developers will not help "
                        "you with this issue and will refer you to the plugin developers."
                    )
                else:
                    # built in command msg
                    title = "Internal Error"
                    msg = (
                        "Something went wrong internally in the command you were trying to execute. "
                        "Please report this error and what you were trying to do to the bot developers."
                    )
                logger.debug(ctx.command.callback.__module__)
                embed = self.error_embed(title, msg)

        # TODO: this has a fundamental problem with any BotMissingPermissions error
        # if the issue is the bot does not have permissions to send embeds or send messages...
        # yeah, problematic.

        if not should_respond:
            logger.debug(
                "Not responding to error since should_respond is falsey because either "
                "the embed has already been sent or belongs to a hidden command and thus should be hidden."
            )
            return

        if embed is None:
            embed = self.error_embed(self.get_title_from_name(error), str(error))

        await ctx.send(embeds=[embed])


def setup(bot: ModmailBot) -> None:
    """Add the error handler to the bot."""
    bot.add_cog(ErrorHandler(bot))
