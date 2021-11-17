"""
Meta test file for tests/mocks.py.

Original Source:
https://github.com/python-discord/bot/blob/d183d03fa2939bebaac3da49646449fdd4d00e6c/tests/test_helpers.py # noqa: E501

NOTE: THIS FILE WAS REWRITTEN TO USE PYTEST


MIT License

Copyright (c) 2018 Python Discord

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import asyncio
import typing
import unittest.mock

import arrow
import discord
import discord.ext.commands
import pytest

from tests import mocks


class TestDiscordMocks:
    """Tests for our specialized discord.py mocks."""

    @pytest.mark.parametrize(
        ["mock_class", "counterpart", "mock_args"],
        [
            [mocks.MockRole, discord.Role, {"name": "role", "position": 1, "mention": "&role"}],
            [
                mocks.MockMember,
                discord.Member,
                {
                    "name": "member",
                    "roles": [mocks.MockRole(name="@everyone", position=1, id=0)],
                    "mention": "@member",
                },
            ],
            [
                mocks.MockGuild,
                discord.Guild,
                {"roles": [mocks.MockRole(name="@everyone", position=1, id=0)], "members": []},
            ],
            [mocks.MockBot, discord.ext.commands.Bot, {}],
        ],
    )
    def test_mock_obj_default_initialization(
        self, mock_class: typing.Any, counterpart: typing.Any, mock_args: dict
    ):
        """Test if the default initialization of a mock object results in the correct object."""
        obj = mock_class()

        # The `spec` argument makes sure `isinstance` checks with mocks pass
        assert isinstance(obj, counterpart)

        for k, v in mock_args.items():
            assert getattr(obj, k) == v

    @pytest.mark.parametrize(
        ["mock_class", "mock_args", "extra_mock_args"],
        [
            [
                mocks.MockRole,
                {
                    "name": "Admins",
                    "position": 10,
                    "id": mocks.generate_realistic_id(arrow.get(1517133142)),
                },
                {"mention": "&Admins"},
            ],
            [
                mocks.MockMember,
                {"name": "arl", "id": mocks.generate_realistic_id(arrow.get(1620350090))},
                {"mention": "@arl"},
            ],
            [
                mocks.MockGuild,
                {"members": []},
                {"roles": [mocks.MockRole(name="@everyone", position=1, id=0)]},
            ],
            [mocks.MockVoiceChannel, {}, {"mention": "#voice_channel"}],
        ],
    )
    def test_mock_obj_initialization_with_args(
        self, mock_class: typing.Any, mock_args: dict, extra_mock_args: dict
    ):
        """Test if an initialization of a mock object with keywords results in the correct object."""
        obj = mock_class(**mock_args)

        mock_args.update(extra_mock_args)
        for k, v in mock_args.items():
            assert v == getattr(obj, k)

    def test_mock_role_uses_position_for_less_than_greater_than(self):
        """Test if `<` and `>` comparisons for MockRole are based on its position attribute."""
        role_one = mocks.MockRole(position=1)
        role_two = mocks.MockRole(position=2)
        role_three = mocks.MockRole(position=3)

        assert role_one < role_two
        assert role_one < role_three
        assert role_two < role_three
        assert role_three > role_two
        assert role_three > role_one
        assert role_two > role_one

    def test_mock_guild_alternative_arguments(self):
        """Test if MockGuild initializes with the arguments provided."""
        core_developer = mocks.MockRole(name="Core Developer", position=2)
        guild = mocks.MockGuild(
            roles=[core_developer],
            members=[mocks.MockMember(id=54321)],
        )

        assert guild.roles == [mocks.MockRole(name="@everyone", position=1, id=0), core_developer]
        assert guild.members == [mocks.MockMember(id=54321)]

    def test_mock_guild_accepts_dynamic_arguments(self):
        """Test if MockGuild accepts and sets arbitrary keyword arguments."""
        guild = mocks.MockGuild(
            emojis=(":hyperjoseph:", ":pensive_ela:"),
            premium_subscription_count=15,
        )

        assert guild.emojis == (":hyperjoseph:", ":pensive_ela:")
        assert guild.premium_subscription_count == 15

    def test_mock_context_default_initialization(self):
        """Tests if MockContext initializes with the correct values."""
        context = mocks.MockContext()

        # The `spec` argument makes sure `isinstance` checks with `discord.ext.commands.Context` pass
        assert isinstance(context, discord.ext.commands.Context)

        assert isinstance(context.bot, mocks.MockBot)
        assert isinstance(context.guild, mocks.MockGuild)
        assert isinstance(context.author, mocks.MockMember)
        assert isinstance(context.message, mocks.MockMessage)

        # ensure that the mocks are the same attributes, like discord.py
        assert context.message.channel is context.channel
        assert context.channel.guild is context.guild

        # ensure the me instance is of the right type and is shared among mock attributes.
        assert isinstance(context.me, mocks.MockMember)
        assert context.me is context.guild.me

    @pytest.mark.parametrize(
        ["mock", "valid_attribute"],
        [
            [mocks.MockGuild, "name"],
            [mocks.MockRole, "hoist"],
            [mocks.MockMember, "display_name"],
            [mocks.MockBot, "user"],
            [mocks.MockContext, "invoked_with"],
            [mocks.MockTextChannel, "last_message"],
            [mocks.MockMessage, "mention_everyone"],
        ],
    )
    def test_mocks_allows_access_to_attributes_part_of_spec(self, mock, valid_attribute: str):
        """Accessing attributes that are valid for the objects they mock should succeed."""
        mock = mock()
        try:
            getattr(mock, valid_attribute)
        except AttributeError:  # pragma: nocover
            msg = f"accessing valid attribute `{valid_attribute}` raised an AttributeError"
            pytest.fail(msg)

    @pytest.mark.parametrize(
        ["mock"],
        [
            [mocks.MockBot],
            [mocks.MockCategoryChannel],
            [mocks.MockContext],
            [mocks.MockClientUser],
            [mocks.MockDMChannel],
            [mocks.MockGuild],
            [mocks.MockMember],
            [mocks.MockMessage],
            [mocks.MockRole],
            [mocks.MockTextChannel],
            [mocks.MockThread],
            [mocks.MockUser],
            [mocks.MockVoiceChannel],
        ],
    )
    def test_mocks_rejects_access_to_attributes_not_part_of_spec(self, mock):
        """Accessing attributes that are invalid for the objects they mock should fail."""
        mock = mock()
        with pytest.raises(AttributeError):
            mock.the_cake_is_a_lie

    @pytest.mark.parametrize(
        ["mock_type", "provided_mention"],
        [
            [mocks.MockClientUser, "client_user mention"],
            [mocks.MockMember, "member mention"],
            [mocks.MockRole, "role mention"],
            [mocks.MockTextChannel, "channel mention"],
            [mocks.MockThread, "thread mention"],
            [mocks.MockUser, "user mention"],
        ],
    )
    def test_mocks_use_mention_when_provided_as_kwarg(self, mock_type, provided_mention: str):
        """The mock should use the passed `mention` instead of the default one if present."""
        mock = mock_type(mention=provided_mention)
        assert mock.mention == provided_mention

    def test_create_test_on_mock_bot_closes_passed_coroutine(self):
        """`bot.loop.create_task` should close the passed coroutine object to prevent warnings."""

        async def dementati():  # pragma: nocover
            """Dummy coroutine for testing purposes."""
            pass

        coroutine_object = dementati()

        bot = mocks.MockBot()
        bot.loop.create_task(coroutine_object)
        with pytest.raises(RuntimeError) as error:
            asyncio.run(coroutine_object)
        assert error.match("cannot reuse already awaited coroutine")


HASHABLE_MOCKS = (
    mocks.MockRole,
    mocks.MockMember,
    mocks.MockGuild,
    mocks.MockTextChannel,
    mocks.MockVoiceChannel,
)


class TestMockObjects:
    """Tests the mock objects and mixins we've defined."""

    def test_colour_mixin(self):
        """Test if the ColourMixin adds aliasing of color -> colour for child classes."""

        class MockHemlock(unittest.mock.MagicMock, mocks.ColourMixin):
            pass

        hemlock = MockHemlock()
        hemlock.color = 1
        assert hemlock.colour == 1
        assert hemlock.colour == hemlock.color

        hemlock.accent_color = 123
        assert hemlock.accent_colour == 123
        assert hemlock.accent_colour == hemlock.accent_color

    def test_hashable_mixin_hash_returns_id(self):
        """Test the HashableMixing uses the id attribute for hashing."""

        class MockScragly(unittest.mock.Mock, mocks.HashableMixin):
            pass

        scragly = MockScragly()
        scragly.id = 10 << 22
        assert hash(scragly) == scragly.id >> 22

    def test_hashable_mixin_uses_id_for_equality_comparison(self):
        """Test the HashableMixing uses the id attribute for equal comparison."""

        class MockScragly(mocks.HashableMixin):
            pass

        scragly = MockScragly()
        scragly.id = 10
        eevee = MockScragly()
        eevee.id = 10
        python = MockScragly()
        python.id = 20

        assert scragly == eevee
        assert (scragly == python) is False

    def test_hashable_mixin_uses_id_for_inequality_comparison(self):
        """Test if the HashableMixing uses the id attribute for non-equal comparison."""

        class MockScragly(mocks.HashableMixin):
            pass

        scragly = MockScragly()
        scragly.id = 10
        eevee = MockScragly()
        eevee.id = 10
        python = MockScragly()
        python.id = 20

        assert scragly != python
        assert (scragly != eevee) is False

    @pytest.mark.parametrize(["mock_cls"], [[x] for x in HASHABLE_MOCKS])
    def test_mock_class_with_hashable_mixin_uses_id_for_hashing(self, mock_cls):
        """Test if the MagicMock subclasses that implement the HashableMixin use id bitshift for hash."""
        instance = mock_cls(id=100 << 22)
        assert hash(instance) == instance.id >> 22

    @pytest.mark.parametrize(["mock_class"], [[x] for x in HASHABLE_MOCKS])
    def test_mock_class_with_hashable_mixin_uses_id_for_equality(self, mock_class):
        """Test if MagicMocks that implement the HashableMixin use id for equality comparisons."""
        instance_one = mock_class()
        instance_two = mock_class()
        instance_three = mock_class()

        instance_one.id = 10
        instance_two.id = 10
        instance_three.id = 20

        assert instance_one == instance_two
        assert (instance_one == instance_three) is False

    @pytest.mark.parametrize(["mock_class"], [[x] for x in HASHABLE_MOCKS])
    def test_mock_class_with_hashable_mixin_uses_id_for_nonequality(self, mock_class):
        """Test if MagicMocks that implement HashableMixin use id for nonequality comparisons."""
        instance_one = mock_class()
        instance_two = mock_class()
        instance_three = mock_class()

        instance_one.id = 10
        instance_two.id = 10
        instance_three.id = 20

        assert instance_one != instance_three
        assert (instance_one != instance_two) is False

    def test_custom_mock_mixin_accepts_mock_seal(self):
        """The `CustomMockMixin` should support `unittest.mock.seal`."""

        class MyMock(mocks.CustomMockMixin, unittest.mock.MagicMock):

            child_mock_type = unittest.mock.MagicMock
            pass

        mock = MyMock()
        unittest.mock.seal(mock)
        with pytest.raises(AttributeError) as error:
            mock.shirayuki = "hello!"

        assert error.match("shirayuki")

    @pytest.mark.parametrize(
        ["mock_type", "valid_attribute"],
        [
            (mocks.MockGuild, "region"),
            (mocks.MockRole, "mentionable"),
            (mocks.MockMember, "display_name"),
            (mocks.MockBot, "owner_id"),
            (mocks.MockContext, "command_failed"),
            (mocks.MockMessage, "mention_everyone"),
            (mocks.MockEmoji, "managed"),
            (mocks.MockPartialEmoji, "url"),
            (mocks.MockReaction, "me"),
        ],
    )
    def test_spec_propagation_of_mock_subclasses(self, mock_type, valid_attribute: str):
        """Test if the `spec` does not propagate to attributes of the mock object."""
        mock = mock_type()
        assert isinstance(mock, mock_type)
        attribute = getattr(mock, valid_attribute)
        assert isinstance(attribute, mock_type.child_mock_type)

    def test_custom_mock_mixin_mocks_async_magic_methods_with_async_mock(self):
        """The CustomMockMixin should mock async magic methods with an AsyncMock."""

        class MyMock(mocks.CustomMockMixin, unittest.mock.MagicMock):
            pass

        mock = MyMock()
        assert isinstance(mock.__aenter__, unittest.mock.AsyncMock)


class TestReturnTypes:
    """
    Our mocks are designed to automatically return the correct objects based on certain methods.

    Eg, ctx.send should return a message object.
    """

    @pytest.mark.parametrize(
        "mock_cls",
        [
            mocks.MockClientUser,
            mocks.MockGuild,
            mocks.MockMember,
            mocks.MockMessage,
            mocks.MockTextChannel,
            mocks.MockVoiceChannel,
            mocks.MockWebhook,
        ],
    )
    @pytest.mark.asyncio
    async def test_edit_returns_same_class(self, mock_cls):
        """Edit methods return a new instance of the same type."""
        mock = mock_cls()

        new_mock = await mock.edit()

        assert isinstance(new_mock, type(mock_cls.spec_set))

    @pytest.mark.parametrize(
        "mock_cls",
        [
            mocks.MockMember,
            mocks.MockTextChannel,
            mocks.MockThread,
            mocks.MockUser,
        ],
    )
    @pytest.mark.asyncio
    async def test_messageable_send_returns_message(self, mock_cls):
        """Ensure that channel objects return mocked messages when sending messages."""
        messageable = mock_cls()

        msg = await messageable.send("hi")

        print(type(msg))
        assert isinstance(msg, discord.Message)

    @pytest.mark.parametrize(
        "mock_cls",
        [mocks.MockMessage, mocks.MockTextChannel],
    )
    @pytest.mark.asyncio
    async def test_thread_create_returns_thread(self, mock_cls):
        """Thread create methods should return a MockThread."""
        mock = mock_cls()

        thread = await mock.create_thread()

        assert isinstance(thread, discord.Thread)


class TestMocksNotCallable:
    """All discord.py mocks are not callable objects, so the mocks should not be either ."""

    @pytest.mark.parametrize("factory", mocks.COPYABLE_MOCKS.values())
    def test_not_callable(self, factory):
        """Assert all mocks aren't callable."""
        instance = factory()
        with pytest.raises(TypeError, match=f"'{type(instance).__name__}' object is not callable"):
            instance()
