import logging
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

    @commands.command()
    async def cmd(self, ctx: commands.Context, error: str = None, *args) -> None:
        """."""
        if error is not None:
            raise getattr(commands, error)(*args)
        else:
            await ctx.send("oop")

    @staticmethod
    def error_embed(message: str, title: str = None) -> discord.Embed:
        """Create an error embed with an error colour and reason and return it."""
        return discord.Embed(message, colour=ERROR_COLOUR, title=title or "Error occured")

    async def handle_user_input_error(
        self, ctx: commands.Context, error: commands.UserInputError
    ) -> discord.Embed:
        """Handling deferred from main error handler to handle UserInputErrors."""
        embed = None
        if isinstance(error, commands.BadArgument):
            embed = self.error_embed(str(error), title="Bad argument")
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = self.error_embed(str(error), title="Missing required argument")
        elif isinstance(error, commands.TooManyArguments):
            embed = self.error_embed(str(error), title="Too many arguments")
        elif isinstance(error, commands.BadUnionArgument):
            # TODO: complete
            msg = ""
            embed = self.error_embed(msg, title="Bad union argument")
        elif isinstance(error, commands.BadLiteralArgument):
            # TODO: complete
            msg = ""
            embed = self.error_embed(msg, title="Bad literal argument")
        elif isinstance(error, commands.ArgumentParsingError):
            embed = self.error_embed(str(error), title="Argument parsing error")
            if isinstance(error, commands.UnexpectedQuoteError):
                ...
            elif isinstance(error, commands.InvalidEndOfQuotedStringError):
                ...
            elif isinstance(error, commands.ExpectedClosingQuoteError):
                ...
            else:
                ...
        else:
            ...
        return embed

    async def handle_check_failure(self, ctx: commands.Context, error: commands.CheckFailure) -> ...:
        """Handle CheckFailures seperately given that there are many of them."""
        ...

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
            ...
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
            logger.error(f"Error occured in {ctx.command}.", exc_info=error.original)
            # todo: this should log somewhere else since this is a bot bug.
            embed = self.error_embed(
                "Oops! Something went wrong internally in the command you were trying to execute. "
                "Please report this error and what you were trying to do to the developer."
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
