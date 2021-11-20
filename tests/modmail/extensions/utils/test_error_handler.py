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


@pytest.mark.parametrize("is_cooldown", [True, False])
def test_reset_cooldown(ctx, cog, is_cooldown: bool):
    """Test the cooldown is reset if the command is on a cooldown."""
    ctx.command.is_on_cooldown.return_value = bool(is_cooldown)
    cog._reset_command_cooldown(ctx)
    assert 1 == ctx.command.is_on_cooldown.call_count
    assert int(is_cooldown) == ctx.command.reset_cooldown.call_count
    if int(is_cooldown) == 1:
        ctx.command.reset_cooldown.assert_called_once_with(ctx)


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


@pytest.mark.parametrize("reset_cooldown", [True, False])
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
    cog: ErrorHandler,
    ctx: mocks.MockContext,
    error: commands.UserInputError,
    title: str,
    description: str,
    reset_cooldown: bool,
):
    """Test user input errors are handled properly."""
    with unittest.mock.patch.object(cog, "_reset_command_cooldown") as mock_cooldown_reset:
        embed = await cog.handle_user_input_error(ctx=ctx, error=error, reset_cooldown=reset_cooldown)

    assert title == embed.title
    assert description == embed.description

    if reset_cooldown:
        assert 1 == mock_cooldown_reset.call_count


@pytest.mark.parametrize(
    ["error", "bot_perms", "should_send_channel", "member_perms", "should_send_user", "raise_forbidden"],
    [
        (
            commands.BotMissingPermissions(["manage_guild"]),
            discord.Permissions(read_messages=True, send_messages=True, embed_links=True),
            1,
            discord.Permissions(read_messages=True, send_messages=True, embed_links=True),
            0,
            False,
        ),
        (
            commands.BotMissingPermissions(["administrator"]),
            discord.Permissions(read_messages=True, send_messages=True, manage_guild=True),
            1,
            discord.Permissions(read_messages=True, send_messages=True, embed_links=True),
            0,
            False,
        ),
        (
            commands.BotMissingPermissions(["mention_everyone"]),
            discord.Permissions(read_messages=True, send_messages=True),
            1,
            discord.Permissions(read_messages=True, send_messages=True, embed_links=True),
            0,
            False,
        ),
        (
            commands.BotMissingPermissions(["administrator"]),
            discord.Permissions(read_messages=False, send_messages=False),
            0,
            discord.Permissions(read_messages=False),
            0,
            False,
        ),
        (
            commands.BotMissingPermissions(["change_nickname"]),
            discord.Permissions(read_messages=True, send_messages=True),
            1,
            discord.Permissions(read_messages=True, send_messages=True, administrator=True),
            1,
            False,
        ),
        (
            commands.BotMissingPermissions(["administrator"]),
            discord.Permissions(manage_threads=True, manage_channels=True),
            0,
            discord.Permissions(administrator=True),
            1,
            False,
        ),
        (
            commands.BotMissingPermissions(["change_nickname"]),
            discord.Permissions(read_messages=True, send_messages=True),
            1,
            discord.Permissions(read_messages=True, send_messages=True, administrator=True),
            1,
            True,
        ),
        (
            commands.BotMissingPermissions(["administrator"]),
            discord.Permissions(manage_threads=True, manage_channels=True),
            0,
            discord.Permissions(administrator=True),
            1,
            True,
        ),
    ],
)
@pytest.mark.asyncio
async def test_handle_bot_missing_perms(
    cog: ErrorHandler,
    ctx: mocks.MockContext,
    error: commands.BotMissingPermissions,
    bot_perms: discord.Permissions,
    should_send_channel: int,
    member_perms: discord.Permissions,
    should_send_user: int,
    raise_forbidden: bool,
):
    """
    Test error_handler.handle_bot_missing_perms.

    There are some cases here where the bot is unable to send messages, and that should be clear.
    """

    def mock_permissions_for(member):
        assert isinstance(member, discord.Member)
        if member is ctx.me:
            return bot_perms
        if member is ctx.author:
            return member_perms
        # fail since there is no other kind of user who should be passed here
        pytest.fail("An invalid member or role was passed to ctx.channel.permissions_for")

    if raise_forbidden:
        error_to_raise = discord.Forbidden(unittest.mock.MagicMock(status=403), "no.")
        ctx.author.send.side_effect = error_to_raise
        ctx.message.author.send.side_effect = error_to_raise

    with unittest.mock.patch.object(ctx.channel, "permissions_for", mock_permissions_for):

        await cog.handle_bot_missing_perms(ctx, error)

    assert should_send_channel == ctx.send.call_count + ctx.channel.send.call_count

    # note: this may break depending on dev-mode and relay mode.
    assert should_send_user == ctx.author.send.call_count


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
    with unittest.mock.patch.object(cog, "handle_bot_missing_perms"):
        if isinstance(error, commands.BotMissingPermissions):
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
