import inspect
import typing
import unittest.mock

import discord
import pytest
from discord.ext import commands

from modmail.extensions.utils import error_handler
from modmail.extensions.utils.error_handler import ErrorHandler
from tests import mocks


@pytest.fixture
def cog():
    """Pytest fixture for error_handler."""
    return ErrorHandler(mocks.MockBot())


@pytest.fixture
def ctx():
    """Pytest fixture for MockContext."""
    return mocks.MockContext(channel=mocks.MockTextChannel())


def test_error_embed():
    """Test the error embed method creates the correct embed."""
    title = "Something very drastic went very wrong!"
    message = "seven southern seas are ready to collapse."
    embed = ErrorHandler.error_embed(title=title, message=message)

    assert embed.title == title
    assert embed.description == message
    assert embed.colour == error_handler.ERROR_COLOUR


@pytest.mark.parametrize(
    ["exception_or_str", "expected_str"],
    [
        [commands.NSFWChannelRequired(mocks.MockTextChannel()), "NSFW Channel Required"],
        [commands.CommandNotFound(), "Command Not Found"],
        ["someWEIrdName", "some WE Ird Name"],
    ],
)
def test_get_title_from_name(exception_or_str: typing.Union[Exception, str], expected_str: str):
    """Test the regex works properly for the title from name."""
    result = ErrorHandler.get_title_from_name(exception_or_str)
    assert expected_str == result


@pytest.mark.parametrize(
    ["error", "title", "description"],
    [
        [
            commands.UserInputError("some interesting information."),
            "User Input Error",
            "some interesting information.",
        ],
        [
            commands.MissingRequiredArgument(inspect.Parameter("SomethingSpecial", kind=1)),
            "Missing Required Argument",
            "SomethingSpecial is a required argument that is missing.",
        ],
        [
            commands.GuildNotFound("ImportantGuild"),
            "Guild Not Found",
            'Guild "ImportantGuild" not found.',
        ],
    ],
)
@pytest.mark.asyncio
async def test_handle_user_input_error(
    cog: ErrorHandler, ctx: mocks.MockContext, error: commands.UserInputError, title: str, description: str
):
    """Test user input errors are handled properly. Does not test with BadUnionArgument."""
    embed = await cog.handle_user_input_error(ctx=ctx, error=error, reset_cooldown=False)

    assert title == embed.title
    assert description == embed.description


@pytest.mark.asyncio
async def test_handle_bot_missing_perms(cog: ErrorHandler):
    """

    Test error_handler.handle_bot_missing_perms.

    There are some cases here where the bot is unable to send messages, and that should be clear.
    """
    ...


@pytest.mark.asyncio
async def test_handle_check_failure(cog: ErrorHandler):
    """
    Test check failures.

    In some cases, this method should result in calling a bot_missing_perms method
    because the bot cannot send messages.
    """
    ...


@pytest.mark.asyncio
async def test_on_command_error(cog: ErrorHandler):
    """Test the general command error method."""
    ...


class TestErrorHandler:
    """
    Test class for the error handler. The problem here is a lot of the errors need to be raised.

    Thankfully, most of them do not have extra attributes that we use, and can be easily faked.
    """

    errors = {
        commands.CommandError: [
            commands.ConversionError,
            {
                commands.UserInputError: [
                    commands.MissingRequiredArgument,
                    commands.TooManyArguments,
                    {
                        commands.BadArgument: [
                            commands.MessageNotFound,
                            commands.MemberNotFound,
                            commands.GuildNotFound,
                            commands.UserNotFound,
                            commands.ChannelNotFound,
                            commands.ChannelNotReadable,
                            commands.BadColourArgument,
                            commands.RoleNotFound,
                            commands.BadInviteArgument,
                            commands.EmojiNotFound,
                            commands.GuildStickerNotFound,
                            commands.PartialEmojiConversionFailure,
                            commands.BadBoolArgument,
                            commands.ThreadNotFound,
                        ]
                    },
                    commands.BadUnionArgument,
                    commands.BadLiteralArgument,
                    {
                        commands.ArgumentParsingError: [
                            commands.UnexpectedQuoteError,
                            commands.InvalidEndOfQuotedStringError,
                            commands.ExpectedClosingQuoteError,
                        ]
                    },
                ]
            },
            commands.CommandNotFound,
            {
                commands.CheckFailure: [
                    commands.CheckAnyFailure,
                    commands.PrivateMessageOnly,
                    commands.NoPrivateMessage,
                    commands.NotOwner,
                    commands.MissingPermissions,
                    commands.BotMissingPermissions,
                    commands.MissingRole,
                    commands.BotMissingRole,
                    commands.MissingAnyRole,
                    commands.BotMissingAnyRole,
                    commands.NSFWChannelRequired,
                ]
            },
            commands.DisabledCommand,
            commands.CommandInvokeError,
            commands.CommandOnCooldown,
            commands.MaxConcurrencyReached,
        ]
    }
