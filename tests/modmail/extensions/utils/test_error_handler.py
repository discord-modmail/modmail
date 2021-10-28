import copy
import inspect
import typing
import unittest.mock

import discord
import pytest
from discord.ext import commands

from modmail.extensions.utils import error_handler
from modmail.extensions.utils.error_handler import ErrorHandler
from tests import mocks


# set dev mode for the cog to a truthy value
error_handler.ANY_DEV_MODE = 2


@pytest.fixture
def cog():
    """Pytest fixture for error_handler."""
    return ErrorHandler(mocks.MockBot())


@pytest.fixture
def ctx():
    """Pytest fixture for MockContext."""
    return mocks.MockContext()


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
        [
            commands.BadUnionArgument(
                inspect.Parameter("colour", 2),
                (commands.InviteConverter, commands.ColourConverter),
                [commands.BadBoolArgument("colour"), commands.BadColourArgument("colour")],
            ),
            "Bad Union Argument",
            'Could not convert "colour" into Invite Converter or Colour Converter.',
        ],
    ],
)
@pytest.mark.asyncio
async def test_handle_user_input_error(
    cog: ErrorHandler, ctx: mocks.MockContext, error: commands.UserInputError, title: str, description: str
):
    """Test user input errors are handled properly."""
    embed = await cog.handle_user_input_error(ctx=ctx, error=error, reset_cooldown=False)

    assert title == embed.title
    assert description == embed.description


@pytest.mark.parametrize(
    ["error", "perms"],
    [],
)
@pytest.mark.asyncio
async def test_handle_bot_missing_perms_only_send(
    cog: ErrorHandler,
    ctx: mocks.MockContext,
    error: commands.BotMissingPermissions,
    perms: discord.Permissions,
):
    """
    Test error_handler.handle_bot_missing_perms.

    There are some cases here where the bot is unable to send messages, and that should be clear.
    """

    def mock_permissions_for(member):
        assert isinstance(member, discord.Member)
        return perms

    ctx.channel.permissions_for = mock_permissions_for

    await cog.handle_bot_missing_perms(ctx, error)

    assert 1 == ctx.send.call_count + ctx.channel.send.call_count


@pytest.mark.parametrize(
    [
        "error",
        "perms",
        "expected_send_to_channel",
        "expected_send_to_author",
        "raise_forbidden",
    ],
    [
        [
            commands.BotMissingPermissions(["manage_guild"]),
            discord.Permissions(send_messages=True, embed_links=True),
            1,
            0,
            False,
        ],
        [
            commands.BotMissingPermissions(["manage_guild"]),
            discord.Permissions(send_messages=True),
            1,
            0,
            False,
        ],
        [
            commands.BotMissingPermissions(["manage_guild"]),
            discord.Permissions(manage_roles=True),
            0,
            1,
            False,
        ],
        [
            commands.BotMissingPermissions(["manage_guild"]),
            discord.Permissions(0),
            0,
            0,
            False,
        ],
        [
            commands.BotMissingPermissions(["manage_guild"]),
            discord.Permissions(manage_channels=True),
            0,
            1,
            True,
        ],
    ],
)
@pytest.mark.asyncio
async def test_handle_bot_missing_perms(
    cog: ErrorHandler,
    ctx: mocks.MockContext,
    error: commands.BotMissingPermissions,
    perms: discord.Permissions,
    raise_forbidden: bool,
    expected_send_to_channel: int,
    expected_send_to_author: int,
):
    """
    Test error_handler.handle_bot_missing_perms.

    There are some cases here where the bot is unable to send messages, and that is tested below.
    """

    def mock_permissions_for(member, /):
        assert isinstance(member, discord.Member)
        return perms

    def not_allowed(*args, **kwargs):
        raise discord.Forbidden(unittest.mock.MagicMock(status=403), "no.")

    ctx.channel.permissions_for = mock_permissions_for

    if raise_forbidden:
        ctx.author.send.side_effect = not_allowed
        ctx.message.author.send.side_effect = not_allowed

    await cog.handle_bot_missing_perms(ctx, error)

    assert expected_send_to_channel == ctx.send.call_count + ctx.channel.send.call_count

    assert expected_send_to_author == ctx.author.send.call_count


@pytest.mark.parametrize(
    ["error", "expected_title"],
    [
        [
            commands.CheckAnyFailure(
                ["Something went wrong"],
                [commands.NoPrivateMessage(), commands.PrivateMessageOnly()],
            ),
            "Something went wrong",
        ],
        [commands.NoPrivateMessage(), "Server Only"],
        [commands.PrivateMessageOnly(), "DMs Only"],
        [commands.NotOwner(), "Not Owner"],
        [commands.MissingPermissions(["send_message"]), "Missing Permissions"],
        [commands.BotMissingPermissions(["send_message"]), None],
        [commands.MissingRole(mocks.MockRole().id), "Missing Role"],
        [commands.BotMissingRole(mocks.MockRole().id), "Bot Missing Role"],
        [commands.MissingAnyRole([mocks.MockRole().id]), "Missing Any Role"],
        [commands.BotMissingAnyRole([mocks.MockRole().id]), "Bot Missing Any Role"],
        [commands.NSFWChannelRequired(mocks.MockTextChannel()), "NSFW Channel Required"],
    ],
)
@pytest.mark.asyncio
async def test_handle_check_failure(
    cog: ErrorHandler, ctx: mocks.MockContext, error: commands.CheckFailure, expected_title: str
):
    """
    Test check failures.

    In some cases, this method should result in calling a bot_missing_perms method
    because the bot cannot send messages.
    """
    if isinstance(error, commands.BotMissingPermissions):
        cog = copy.copy(cog)
        cog.handle_bot_missing_perms = unittest.mock.AsyncMock()
        assert await cog.handle_check_failure(ctx, error) is None
        return

    embed = await cog.handle_check_failure(ctx, error)
    assert embed.title == expected_title


@pytest.mark.parametrize(["error", "msg"], [[commands.CommandNotFound(), None]])
@pytest.mark.asyncio
async def test_on_command_error(
    cog: ErrorHandler, ctx: mocks.MockContext, error: commands.CommandError, msg: discord.Message
):
    """Test the general command error method."""
    res = await cog.on_command_error(ctx, error)
    assert msg == res


@pytest.mark.asyncio
async def test_on_command_error_ignore_already_handled(cog: ErrorHandler, ctx: mocks.MockContext):
    """Assert errors handled elsewhere are ignored."""
    error = commands.NotOwner()
    error.handled = True
    assert await cog.on_command_error(ctx, error) is None


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
