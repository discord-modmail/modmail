"""
Meta test file for tests/mocks.py.

Original Source:
https://github.com/python-discord/bot/blob/d183d03fa2939bebaac3da49646449fdd4d00e6c/tests/test_helpers.py # noqa: E501

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
import unittest
import unittest.mock

import discord

from tests import mocks as test_mocks


class DiscordMocksTests(unittest.TestCase):
    """Tests for our specialized discord.py mocks."""

    def test_mock_role_default_initialization(self):
        """Test if the default initialization of MockRole results in the correct object."""
        role = test_mocks.MockRole()

        # The `spec` argument makes sure `isistance` checks with `discord.Role` pass
        self.assertIsInstance(role, discord.Role)

        self.assertEqual(role.name, "role")
        self.assertEqual(role.position, 1)
        self.assertEqual(role.mention, "&role")

    def test_mock_role_alternative_arguments(self):
        """Test if MockRole initializes with the arguments provided."""
        role = test_mocks.MockRole(
            name="Admins",
            id=90210,
            position=10,
        )

        self.assertEqual(role.name, "Admins")
        self.assertEqual(role.id, 90210)
        self.assertEqual(role.position, 10)
        self.assertEqual(role.mention, "&Admins")

    def test_mock_role_accepts_dynamic_arguments(self):
        """Test if MockRole accepts and sets abitrary keyword arguments."""
        role = test_mocks.MockRole(
            guild="Dino Man",
            hoist=True,
        )

        self.assertEqual(role.guild, "Dino Man")
        self.assertTrue(role.hoist)

    def test_mock_role_uses_position_for_less_than_greater_than(self):
        """Test if `<` and `>` comparisons for MockRole are based on its position attribute."""
        role_one = test_mocks.MockRole(position=1)
        role_two = test_mocks.MockRole(position=2)
        role_three = test_mocks.MockRole(position=3)

        self.assertLess(role_one, role_two)
        self.assertLess(role_one, role_three)
        self.assertLess(role_two, role_three)
        self.assertGreater(role_three, role_two)
        self.assertGreater(role_three, role_one)
        self.assertGreater(role_two, role_one)

    def test_mock_member_default_initialization(self):
        """Test if the default initialization of Mockmember results in the correct object."""
        member = test_mocks.MockMember()

        # The `spec` argument makes sure `isistance` checks with `discord.Member` pass
        self.assertIsInstance(member, discord.Member)

        self.assertEqual(member.name, "member")
        self.assertListEqual(member.roles, [test_mocks.MockRole(name="@everyone", position=1, id=0)])
        self.assertEqual(member.mention, "@member")

    def test_mock_member_alternative_arguments(self):
        """Test if MockMember initializes with the arguments provided."""
        core_developer = test_mocks.MockRole(name="Core Developer", position=2)
        member = test_mocks.MockMember(name="Mark", id=12345, roles=[core_developer])

        self.assertEqual(member.name, "Mark")
        self.assertEqual(member.id, 12345)
        self.assertListEqual(
            member.roles, [test_mocks.MockRole(name="@everyone", position=1, id=0), core_developer]
        )
        self.assertEqual(member.mention, "@Mark")

    def test_mock_member_accepts_dynamic_arguments(self):
        """Test if MockMember accepts and sets abitrary keyword arguments."""
        member = test_mocks.MockMember(
            nick="Dino Man",
            colour=discord.Colour.default(),
        )

        self.assertEqual(member.nick, "Dino Man")
        self.assertEqual(member.colour, discord.Colour.default())

    def test_mock_guild_default_initialization(self):
        """Test if the default initialization of Mockguild results in the correct object."""
        guild = test_mocks.MockGuild()

        # The `spec` argument makes sure `isistance` checks with `discord.Guild` pass
        self.assertIsInstance(guild, discord.Guild)

        self.assertListEqual(guild.roles, [test_mocks.MockRole(name="@everyone", position=1, id=0)])
        self.assertListEqual(guild.members, [])

    def test_mock_guild_alternative_arguments(self):
        """Test if MockGuild initializes with the arguments provided."""
        core_developer = test_mocks.MockRole(name="Core Developer", position=2)
        guild = test_mocks.MockGuild(
            roles=[core_developer],
            members=[test_mocks.MockMember(id=54321)],
        )

        self.assertListEqual(
            guild.roles, [test_mocks.MockRole(name="@everyone", position=1, id=0), core_developer]
        )
        self.assertListEqual(guild.members, [test_mocks.MockMember(id=54321)])

    def test_mock_guild_accepts_dynamic_arguments(self):
        """Test if MockGuild accepts and sets abitrary keyword arguments."""
        guild = test_mocks.MockGuild(
            emojis=(":hyperjoseph:", ":pensive_ela:"),
            premium_subscription_count=15,
        )

        self.assertTupleEqual(guild.emojis, (":hyperjoseph:", ":pensive_ela:"))
        self.assertEqual(guild.premium_subscription_count, 15)

    def test_mock_bot_default_initialization(self):
        """Tests if MockBot initializes with the correct values."""
        bot = test_mocks.MockBot()

        # The `spec` argument makes sure `isistance` checks with `discord.ext.commands.Bot` pass
        self.assertIsInstance(bot, discord.ext.commands.Bot)

    def test_mock_context_default_initialization(self):
        """Tests if MockContext initializes with the correct values."""
        context = test_mocks.MockContext()

        # The `spec` argument makes sure `isistance` checks with `discord.ext.commands.Context` pass
        self.assertIsInstance(context, discord.ext.commands.Context)

        self.assertIsInstance(context.bot, test_mocks.MockBot)
        self.assertIsInstance(context.guild, test_mocks.MockGuild)
        self.assertIsInstance(context.author, test_mocks.MockMember)

    def test_mocks_allows_access_to_attributes_part_of_spec(self):
        """Accessing attributes that are valid for the objects they mock should succeed."""
        mocks = (
            (test_mocks.MockGuild(), "name"),
            (test_mocks.MockRole(), "hoist"),
            (test_mocks.MockMember(), "display_name"),
            (test_mocks.MockBot(), "user"),
            (test_mocks.MockContext(), "invoked_with"),
            (test_mocks.MockTextChannel(), "last_message"),
            (test_mocks.MockMessage(), "mention_everyone"),
        )

        for mock, valid_attribute in mocks:
            with self.subTest(mock=mock):
                try:
                    getattr(mock, valid_attribute)
                except AttributeError:
                    msg = f"accessing valid attribute `{valid_attribute}` raised an AttributeError"
                    self.fail(msg)

    @unittest.mock.patch(f"{__name__}.DiscordMocksTests.subTest")
    @unittest.mock.patch(f"{__name__}.getattr")
    def test_mock_allows_access_to_attributes_test(self, mock_getattr, mock_subtest):
        """The valid attribute test should raise an AssertionError after an AttributeError."""
        mock_getattr.side_effect = AttributeError

        msg = "accessing valid attribute `name` raised an AttributeError"
        with self.assertRaises(AssertionError, msg=msg):
            self.test_mocks_allows_access_to_attributes_part_of_spec()

    def test_mocks_rejects_access_to_attributes_not_part_of_spec(self):
        """Accessing attributes that are invalid for the objects they mock should fail."""
        mocks = (
            test_mocks.MockGuild(),
            test_mocks.MockRole(),
            test_mocks.MockMember(),
            test_mocks.MockBot(),
            test_mocks.MockContext(),
            test_mocks.MockTextChannel(),
            test_mocks.MockMessage(),
        )

        for mock in mocks:
            with self.subTest(mock=mock):
                with self.assertRaises(AttributeError):
                    mock.the_cake_is_a_lie

    def test_mocks_use_mention_when_provided_as_kwarg(self):
        """The mock should use the passed `mention` instead of the default one if present."""
        test_cases = (
            (test_mocks.MockRole, "role mention"),
            (test_mocks.MockMember, "member mention"),
            (test_mocks.MockTextChannel, "channel mention"),
        )

        for mock_type, mention in test_cases:
            with self.subTest(mock_type=mock_type, mention=mention):
                mock = mock_type(mention=mention)
                self.assertEqual(mock.mention, mention)

    def test_create_test_on_mock_bot_closes_passed_coroutine(self):
        """`bot.loop.create_task` should close the passed coroutine object to prevent warnings."""

        async def dementati():
            """Dummy coroutine for testing purposes."""

        coroutine_object = dementati()

        bot = test_mocks.MockBot()
        bot.loop.create_task(coroutine_object)
        with self.assertRaises(RuntimeError, msg="cannot reuse already awaited coroutine"):
            asyncio.run(coroutine_object)

    def test_user_mock_uses_explicitly_passed_mention_attribute(self):
        """Ensure MockUser uses an explictly passed value for user.mention."""
        user = test_mocks.MockUser(mention="hello")
        self.assertEqual(user.mention, "hello")


class MockObjectTests(unittest.TestCase):
    """Tests the mock objects and mixins we've defined."""

    @classmethod
    def setUpClass(cls):
        """Called by unittest before running the test methods."""
        cls.hashable_mocks = (test_mocks.MockRole, test_mocks.MockMember, test_mocks.MockGuild)

    def test_colour_mixin(self):
        """Test if the ColourMixin adds aliasing of color -> colour for child classes."""

        class MockHemlock(unittest.mock.MagicMock, test_mocks.ColourMixin):
            pass

        hemlock = MockHemlock()
        hemlock.color = 1
        self.assertEqual(hemlock.colour, 1)
        self.assertEqual(hemlock.colour, hemlock.color)

    def test_hashable_mixin_hash_returns_id(self):
        """Test the HashableMixing uses the id attribute for hashing."""

        class MockScragly(unittest.mock.Mock, test_mocks.HashableMixin):
            pass

        scragly = MockScragly()
        scragly.id = 10
        self.assertEqual(hash(scragly), scragly.id)

    def test_hashable_mixin_hash_returns_id_bitshift(self):
        """Test the HashableMixing uses the id attribute for hashing when above 1<<22."""

        class MockScragly(unittest.mock.Mock, test_mocks.HashableMixin):
            pass

        scragly = MockScragly()
        scragly.id = 10 << 22
        self.assertEqual(hash(scragly), scragly.id >> 22)

    def test_hashable_mixin_uses_id_for_equality_comparison(self):
        """Test the HashableMixing uses the id attribute for equal comparison."""

        class MockScragly(test_mocks.HashableMixin):
            pass

        scragly = MockScragly()
        scragly.id = 10
        eevee = MockScragly()
        eevee.id = 10
        python = MockScragly()
        python.id = 20

        self.assertTrue(scragly == eevee)
        self.assertFalse(scragly == python)

    def test_hashable_mixin_uses_id_for_nonequality_comparison(self):
        """Test if the HashableMixing uses the id attribute for non-equal comparison."""

        class MockScragly(test_mocks.HashableMixin):
            pass

        scragly = MockScragly()
        scragly.id = 10
        eevee = MockScragly()
        eevee.id = 10
        python = MockScragly()
        python.id = 20

        self.assertTrue(scragly != python)
        self.assertFalse(scragly != eevee)

    def test_mock_class_with_hashable_mixin_uses_id_for_hashing(self):
        """Test if the MagicMock subclasses that implement the HashableMixin use id for hash."""
        for mock in self.hashable_mocks:
            with self.subTest(mock_class=mock):
                instance = test_mocks.MockRole(id=100)
                self.assertEqual(hash(instance), instance.id)

    def test_mock_class_with_hashable_mixin_uses_id_for_equality(self):
        """Test if MagicMocks that implement the HashableMixin use id for equality comparisons."""
        for mock_class in self.hashable_mocks:
            with self.subTest(mock_class=mock_class):
                instance_one = mock_class()
                instance_two = mock_class()
                instance_three = mock_class()

                instance_one.id = 10
                instance_two.id = 10
                instance_three.id = 20

                self.assertTrue(instance_one == instance_two)
                self.assertFalse(instance_one == instance_three)

    def test_mock_class_with_hashable_mixin_uses_id_for_nonequality(self):
        """Test if MagicMocks that implement HashableMixin use id for nonequality comparisons."""
        for mock_class in self.hashable_mocks:
            with self.subTest(mock_class=mock_class):
                instance_one = mock_class()
                instance_two = mock_class()
                instance_three = mock_class()

                instance_one.id = 10
                instance_two.id = 10
                instance_three.id = 20

                self.assertFalse(instance_one != instance_two)
                self.assertTrue(instance_one != instance_three)

    def test_custom_mock_mixin_accepts_mock_seal(self):
        """The `CustomMockMixin` should support `unittest.mock.seal`."""

        class MyMock(test_mocks.CustomMockMixin, unittest.mock.MagicMock):

            child_mock_type = unittest.mock.MagicMock
            pass

        mock = MyMock()
        unittest.mock.seal(mock)
        with self.assertRaises(AttributeError, msg="MyMock.shirayuki"):
            mock.shirayuki = "hello!"

    def test_spec_propagation_of_mock_subclasses(self):
        """Test if the `spec` does not propagate to attributes of the mock object."""
        test_values = (
            (test_mocks.MockGuild, "region"),
            (test_mocks.MockRole, "mentionable"),
            (test_mocks.MockMember, "display_name"),
            (test_mocks.MockBot, "owner_id"),
            (test_mocks.MockContext, "command_failed"),
            (test_mocks.MockMessage, "mention_everyone"),
            (test_mocks.MockEmoji, "managed"),
            (test_mocks.MockPartialEmoji, "url"),
            (test_mocks.MockReaction, "me"),
        )

        for mock_type, valid_attribute in test_values:
            with self.subTest(mock_type=mock_type, attribute=valid_attribute):
                mock = mock_type()
                self.assertTrue(isinstance(mock, mock_type))
                attribute = getattr(mock, valid_attribute)
                self.assertTrue(isinstance(attribute, mock_type.child_mock_type))

    def test_custom_mock_mixin_mocks_async_magic_methods_with_async_mock(self):
        """The CustomMockMixin should mock async magic methods with an AsyncMock."""

        class MyMock(test_mocks.CustomMockMixin, unittest.mock.MagicMock):
            pass

        mock = MyMock()
        self.assertIsInstance(mock.__aenter__, unittest.mock.AsyncMock)
