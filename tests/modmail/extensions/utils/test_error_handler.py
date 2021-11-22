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


@pytest.fixture
def command():
    """Fixture for discord.ext.commands.Command."""
    command = unittest.mock.NonCallableMock(spec_set=commands.Command(unittest.mock.AsyncMock(), name="mock"))
    return command


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


class TestCommandInvokeError:
    """
    Collection of tests for ErrorHandler.handle_command_invoke_error.

    This serves as nothing more but to group the tests for the single method
    """

    @pytest.mark.asyncio
    async def test_forbidden(self, cog: ErrorHandler, ctx: mocks.MockContext):
        """Test discord.Forbidden errors are not met with an attempt to send a message."""
        error = commands.CommandInvokeError(unittest.mock.Mock(spec_set=discord.Forbidden))
        with unittest.mock.patch.object(cog, "handle_bot_missing_perms"):
            result = await cog.handle_command_invoke_error(ctx, error)

        assert result is None
        assert 0 == ctx.send.call_count

    @pytest.mark.parametrize(
        ["module", "title_words", "message_words", "exclude_words"],
        [
            [
                "modmail.extensions.utils.error_handler",
                ["internal", "error"],
                ["internally", "wrong", "report", "developers"],
                ["plugin"],
            ],
            [
                "modmail.plugins.better_error_handler.main",
                ["plugin", "error"],
                ["plugin", "wrong", "plugin developers"],
                None,
            ],
        ],
    )
    @pytest.mark.asyncio
    async def test_error(
        self,
        cog: ErrorHandler,
        ctx: mocks.MockContext,
        command: commands.Command,
        module: str,
        title_words: list,
        message_words: list,
        exclude_words: list,
    ):
        """Test that the proper alerts are shared in the returned embed."""
        embed = discord.Embed(description="you failed")
        error = commands.CommandInvokeError(Exception("lul"))
        ctx.command = command

        # needs a mock cog for __module__
        mock_cog = unittest.mock.NonCallableMock(spec_set=commands.Cog)
        mock_cog.__module__ = module
        ctx.command.cog = mock_cog

        def error_embed(title, msg):
            """Replace cog.error_embed and test that the correct params are passed."""
            title = title.lower()
            for word in title_words:
                assert word in title

            msg = msg.lower()
            for word in message_words:
                assert word in msg

            if exclude_words:
                for word in exclude_words:
                    assert word not in title
                    assert word not in msg

            return embed

        with unittest.mock.patch.object(cog, "error_embed", side_effect=error_embed):
            result = await cog.handle_command_invoke_error(ctx, error)

        assert result is embed


class TestOnCommandError:
    """
    Collection of tests for ErrorHandler.on_command_error.

    This serves as nothing more but to group the tests for the single method
    """

    @pytest.mark.asyncio
    async def test_ignore_already_handled(self, cog: ErrorHandler, ctx: mocks.MockContext):
        """Assert errors handled elsewhere are ignored."""
        error = commands.NotOwner()
        error.handled = True
        await cog.on_command_error(ctx, error)

    @pytest.mark.asyncio
    async def test_ignore_command_not_found(self, cog: ErrorHandler, ctx: mocks.MockContext):
        """Test the command handler ignores command not found errors."""
        await cog.on_command_error(ctx, commands.CommandNotFound())

        assert 0 == ctx.send.call_count

    @pytest.mark.parametrize(
        ["error", "delegate", "embed"],
        [
            [
                commands.UserInputError("User input the wrong thing I guess, not sure."),
                "handle_user_input_error",
                discord.Embed(description="si"),
            ],
            [
                commands.CheckFailure("Checks failed, crosses passed."),
                "handle_check_failure",
                discord.Embed(description="also si"),
            ],
            [
                commands.CheckFailure("Checks failed, crosses passed."),
                "handle_check_failure",
                None,
            ],
            [
                unittest.mock.NonCallableMock(spec_set=commands.CommandInvokeError),
                "handle_command_invoke_error",
                discord.Embed(description="<generic response>"),
            ],
            [
                unittest.mock.NonCallableMock(spec_set=commands.CommandInvokeError),
                "handle_command_invoke_error",
                None,
            ],
        ],
    )
    @pytest.mark.asyncio
    async def test_errors_delegated(
        self,
        cog: ErrorHandler,
        ctx: mocks.MockContext,
        error: commands.CommandError,
        delegate: str,
        embed: typing.Optional[discord.Embed],
    ):
        """Test that the main error method delegates errors as appropriate to helper methods."""
        with unittest.mock.patch.object(cog, delegate) as mock:
            mock.return_value = embed
            await cog.on_command_error(ctx, error)

        assert 1 == mock.call_count
        assert unittest.mock.call(ctx, error) == mock.call_args

        assert int(bool(embed)) == ctx.send.call_count

        if embed is None:
            return

        assert unittest.mock.call(embeds=[embed]) == ctx.send.call_args

    @pytest.mark.parametrize(
        ["embed", "error", "hidden", "disabled_reason"],
        [
            [
                discord.Embed(description="hey its me your worst error"),
                commands.DisabledCommand("disabled command, yert"),
                True,
                None,
            ],
            [
                discord.Embed(description="hey its me your worst error"),
                commands.DisabledCommand("disabled command, yert"),
                False,
                None,
            ],
            [
                discord.Embed(description="hey its me your worst error"),
                commands.DisabledCommand("disabled command, yert"),
                False,
                "Some message that should show up once the mock is right",
            ],
        ],
    )
    @pytest.mark.asyncio
    async def test_disabled_command(
        self,
        cog: ErrorHandler,
        ctx: mocks.MockContext,
        command: commands.Command,
        embed: discord.Embed,
        error: commands.DisabledCommand,
        hidden: bool,
        disabled_reason: str,
    ):
        """Test disabled commands have the right error message."""

        def error_embed(title: str, message: str):
            if disabled_reason:
                assert disabled_reason in message
            return embed

        ctx.command = command
        ctx.invoked_with = command.name
        ctx.command.hidden = hidden
        ctx.command.extras = dict()
        should_respond = not hidden
        if disabled_reason:
            ctx.command.extras["disabled_reason"] = disabled_reason

        mock = unittest.mock.Mock(side_effect=error_embed)

        with unittest.mock.patch.object(cog, "error_embed", mock):
            await cog.on_command_error(ctx, error)

        assert int(should_respond) == ctx.send.call_count
        if should_respond:
            assert unittest.mock.call(embeds=[embed]) == ctx.send.call_args

    @pytest.mark.asyncio
    async def test_default_embed(self, cog, ctx):
        """Test the default embed calls the right methods the correct number of times."""
        embed = discord.Embed(description="I need all of the errors!")
        error = unittest.mock.NonCallableMock(spec_set=commands.ConversionError)

        with unittest.mock.patch.object(cog, "error_embed") as mock:
            mock.return_value = embed
            await cog.on_command_error(ctx, error)

        assert 1 == ctx.send.call_count
        assert unittest.mock.call(embeds=[embed]) == ctx.send.call_args
