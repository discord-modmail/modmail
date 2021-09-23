import logging
import re
import typing

import discord
import discord.errors
from discord.ext import commands

from modmail.bot import ModmailBot
from modmail.log import ModmailLogger
from modmail.utils.cogs import ExtMetadata, ModmailCog


logger: ModmailLogger = logging.getLogger(__name__)

EXT_METADATA = ExtMetadata()

ERROR_COLOUR = discord.Colour.red()


class ErrorHandler(ModmailCog, name="Error Handler"):
    """Handles all errors across the bot."""

    def __init__(self, bot: ModmailBot):
        self.bot = bot

    @staticmethod
    def error_embed(message: str, title: str = None) -> discord.Embed:
        """Create an error embed with an error colour and reason and return it."""
        return discord.Embed(message, colour=ERROR_COLOUR, title=title or "Error Occured")

    @staticmethod
    def get_title_from_name(error: typing.Union[Exception, str]) -> str:
        """
        Return a message dervived from the exception class name.

        Eg NSFWChannelRequired returns NSFW Channel Required
        """
        if not isinstance(error, str):
            error = error.__class__.__name__
        return re.sub(r"(?<=[a-z])([A-Z])(?=[a-z])", r" \1", error)

    async def handle_user_input_error(
        self, ctx: commands.Context, error: commands.UserInputError
    ) -> discord.Embed:
        """Handling deferred from main error handler to handle UserInputErrors."""
        embed = None
        msg = None
        title = "User Input Error"
        if isinstance(error, commands.BadUnionArgument):
            msg = self.get_title_from_name(str(error))
            title = self.get_title_from_name(error)
        else:
            title = self.get_title_from_name(error)
        return embed or self.error_embed(msg or str(error), title=title)

    async def handle_check_failure(
        self, ctx: commands.Context, error: commands.CheckFailure
    ) -> discord.Embed:
        """Handle CheckFailures seperately given that there are many of them."""
        title = "Check Failure"
        msg = None
        if isinstance(error, commands.CheckAnyFailure):
            title = self.get_title_from_name(error.checks[-1])
            msg = str(error)
        elif isinstance(error, commands.PrivateMessageOnly):
            title = "DMs Only"
        elif isinstance(error, commands.NoPrivateMessage):
            title = "Server Only"
        else:
            title = self.get_title_from_name(error)
        embed = self.error_embed(msg or str(error), title=title)
        return embed

    @ModmailCog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Activates when a command raises an error."""
        if getattr(error, "handled", False):
            logging.debug(f"Command {ctx.command} had its error already handled locally; ignoring.")
            return

        if not isinstance(error, commands.CommandError):
            logger.error("What in the world...")
            return
        logger.trace(error)
        if isinstance(error, commands.CommandNotFound):
            # ignore every time the user inputs a message that starts with our prefix but isn't a command
            # this will be modified in the future to support prefilled commands
            return

        embed: typing.Optional[discord.Embed] = None
        should_respond = True

        if isinstance(error, commands.UserInputError):
            embed = await self.handle_user_input_error(ctx, error)
        elif isinstance(error, commands.CheckFailure):
            embed = await self.handle_check_failure(ctx, error)
        elif isinstance(error, commands.ConversionError):
            s = object()
            error.converter.convert.__annotations__.get("return", s)
            embed = error

        elif isinstance(error, commands.DisabledCommand):
            logger.debug("")
            if ctx.command.hidden:
                should_respond = False
            else:
                msg = f"Command `{ctx.invoked_with}` is disabled."
                if reason := ctx.command.extras.get("disabled_reason", None):
                    msg += f"\nReason: {reason}"
                embed = self.error_embed(msg, title="Command disabled")

        elif isinstance(error, commands.CommandInvokeError):
            # generic error
            logger.error(f'Error occured in command "{ctx.command}".', exc_info=error.original)
            # todo: this should log somewhere else since this is a bot bug.
            embed = self.error_embed(
                "Oops! Something went wrong internally in the command you were trying to execute. "
                "Please report this error and what you were trying to do to the developers."
            )
        elif isinstance(error, commands.CommandOnCooldown):
            ...
        elif isinstance(error, commands.MaxConcurrencyReached):
            ...
        else:
            logger.error("An error was made that was unhandlable.")

        # TODO: this has a fundamental problem with any BotMissingPermissions error
        # if the issue is the bot does not have permissions to send embeds or send messages...
        # yeah, problematic.

        if not should_respond:
            logger.debug("Not responding to error since should_respond is falsey.")
            return

        if embed is not None:
            await ctx.send(embeds=[embed])
        else:
            await ctx.send("Uhm. Something happened. IDK what.")


def setup(bot: ModmailBot) -> None:
    """Add the error handler to the bot."""
    bot.add_cog(ErrorHandler(bot))
