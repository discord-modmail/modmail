"""
Helper methods for testing.

Slight modifications have been made to support our bot.

Original Source:
https://github.com/python-discord/bot/blob/d183d03fa2939bebaac3da49646449fdd4d00e6c/tests/helpers.py# noqa: E501

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
from __future__ import annotations

import asyncio
import collections
import itertools
import logging
import typing
import unittest.mock
from typing import TYPE_CHECKING, Iterable, Optional

import aiohttp
import discord
import discord.mixins
from discord.ext.commands import Context

import modmail.bot


for logger in logging.Logger.manager.loggerDict.values():
    # Set all loggers to CRITICAL by default to prevent screen clutter during testing

    if not isinstance(logger, logging.Logger):
        # There might be some logging.PlaceHolder objects in there
        continue

    logger.setLevel(logging.CRITICAL)


class HashableMixin(discord.mixins.EqualityComparable):
    """
    Mixin that provides similar hashing and equality functionality as discord.py's `Hashable` mixin.

    Given that most of our features need the created_at function to work, we are typically using
    full fake discord ids, and so we still bitshift the id like Dpy does.

    However, given that the hash of 4>>22 and 5>>22 is the same, we check if the number is above 1<<22.
    If so, we hash it. This could result in some weird behavior with the hash of
    1<<22 + 1 equaling 1.
    """

    if TYPE_CHECKING:  # pragma: nocover
        id: int

    def __hash__(self):
        if self.id < 1 << 22:
            return self.id
        else:
            return self.id >> 22


class ColourMixin:
    """A mixin for Mocks that provides the aliasing of (accent_)color->(accent_)colour like discord.py."""

    @property
    def color(self) -> discord.Colour:
        """Alias of colour."""
        return self.colour

    @color.setter
    def color(self, color: discord.Colour) -> None:
        self.colour = color

    @property
    def accent_color(self) -> discord.Colour:
        """Alias of accent_colour."""
        return self.accent_colour

    @accent_color.setter
    def accent_color(self, color: discord.Colour) -> None:
        self.accent_colour = color


class CustomMockMixin:
    """
    Provides common functionality for our custom Mock types.

    The `_get_child_mock` method automatically returns an AsyncMock for coroutine methods of the mock
    object. As discord.py also uses synchronous methods that nonetheless return coroutine objects, the
    class attribute `additional_spec_asyncs` can be overwritten with an iterable containing additional
    attribute names that should also mocked with an AsyncMock instead of a regular MagicMock/Mock. The
    class method `spec_set` can be overwritten with the object that should be uses as the specification
    for the mock.

    Mock/MagicMock subclasses that use this mixin only need to define `__init__` method if they need to
    implement custom behavior.
    """

    child_mock_type = unittest.mock.MagicMock
    discord_id = itertools.count(0)
    spec_set = None
    additional_spec_asyncs = None

    def __init__(self, **kwargs):
        name = kwargs.pop(
            "name", None
        )  # `name` has special meaning for Mock classes, so we need to set it manually.
        super().__init__(spec_set=self.spec_set, **kwargs)

        if self.additional_spec_asyncs:
            self._spec_asyncs.extend(self.additional_spec_asyncs)

        if name:
            self.name = name

    def _get_child_mock(self, **kw):
        """
        Overwrite of the `_get_child_mock` method to stop the propagation of our custom mock classes.

        Mock objects automatically create children when you access an attribute or call a method on them.
        By default, the class of these children is the type of the parent itself.
        However, this would mean that the children created for our custom mock types would also be instances
        of that custom mock type. This is not desirable, as attributes of, e.g., a `Bot` object are not
        `Bot` objects themselves. The Python docs for `unittest.mock` hint that overwriting this method is the
        best way to deal with that.

        This override will look for an attribute called `child_mock_type` and
        use that as the type of the child mock.
        """
        _new_name = kw.get("_new_name")
        if _new_name in self.__dict__["_spec_asyncs"]:
            return unittest.mock.AsyncMock(**kw)

        _type = type(self)
        if issubclass(_type, unittest.mock.MagicMock) and _new_name in unittest.mock._async_method_magics:
            # Any asynchronous magic becomes an AsyncMock
            klass = unittest.mock.AsyncMock
        else:
            klass = self.child_mock_type

        if self._mock_sealed:
            attribute = "." + kw["name"] if "name" in kw else "()"
            mock_name = self._extract_mock_name() + attribute
            raise AttributeError(mock_name)

        return klass(**kw)


# Create a guild instance to get a realistic Mock of `discord.Guild`
guild_data = {
    "id": 1,
    "name": "guild",
    "region": "Europe",
    "verification_level": 2,
    "default_notications": 1,
    "afk_timeout": 100,
    "icon": "icon.png",
    "banner": "banner.png",
    "mfa_level": 1,
    "splash": "splash.png",
    "system_channel_id": 464033278631084042,
    "description": "mocking is fun",
    "max_presences": 10_000,
    "max_members": 100_000,
    "preferred_locale": "UTC",
    "owner_id": 1,
    "afk_channel_id": 464033278631084042,
}
guild_instance = discord.Guild(data=guild_data, state=unittest.mock.MagicMock())


class MockGuild(CustomMockMixin, unittest.mock.Mock, HashableMixin):
    """
    A `Mock` subclass to mock `discord.Guild` objects.

    A MockGuild instance will follow the specifications of a `discord.Guild` instance. This means
    that if the code you're testing tries to access an attribute or method that normally does not
    exist for a `discord.Guild` object this will raise an `AttributeError`. This is to make sure our
    tests fail if the code we're testing uses a `discord.Guild` object in the wrong way.

    One restriction of that is that if the code tries to access an attribute that normally does not
    exist for `discord.Guild` instance but was added dynamically, this will raise an exception with
    the mocked object. To get around that, you can set the non-standard attribute explicitly for the
    instance of `MockGuild`:

    >>> guild = MockGuild()
    >>> guild.attribute_that_normally_does_not_exist = unittest.mock.MagicMock()

    In addition to attribute simulation, mocked guild object will pass an `isinstance` check against
    `discord.Guild`:

    >>> guild = MockGuild()
    >>> isinstance(guild, discord.Guild)
    True

    For more info, see the `Mocking` section in `tests/README.md`.
    """

    spec_set = guild_instance

    def __init__(self, roles: Optional[Iterable[MockRole]] = None, **kwargs) -> None:
        default_kwargs = {"id": next(self.discord_id), "members": []}
        super().__init__(**collections.ChainMap(kwargs, default_kwargs))

        self.roles = [MockRole(name="@everyone", position=1, id=0)]
        if roles:
            self.roles.extend(roles)


# Create a Role instance to get a realistic Mock of `discord.Role`
role_data = {"name": "role", "id": 1}
role_instance = discord.Role(guild=guild_instance, state=unittest.mock.MagicMock(), data=role_data)


class MockRole(CustomMockMixin, unittest.mock.Mock, ColourMixin, HashableMixin):
    """
    A Mock subclass to mock `discord.Role` objects.

    Instances of this class will follow the specifications of `discord.Role` instances. For more
    information, see the `MockGuild` docstring.
    """

    spec_set = role_instance

    def __init__(self, **kwargs) -> None:
        default_kwargs = {
            "id": next(self.discord_id),
            "name": "role",
            "position": 1,
            "colour": discord.Colour(0xDEADBF),
            "permissions": discord.Permissions(),
        }
        super().__init__(**collections.ChainMap(kwargs, default_kwargs))

        if isinstance(self.colour, int):
            self.colour = discord.Colour(self.colour)

        if isinstance(self.permissions, int):
            self.permissions = discord.Permissions(self.permissions)

        if "mention" not in kwargs:
            self.mention = f"&{self.name}"

    def __lt__(self, other):
        """Simplified position-based comparisons similar to those of `discord.Role`."""
        return self.position < other.position

    def __ge__(self, other):
        """Simplified position-based comparisons similar to those of `discord.Role`."""
        return self.position >= other.position


# Create a Member instance to get a realistic Mock of `discord.Member`
member_data = {"user": "lemon", "roles": [1]}
state_mock = unittest.mock.MagicMock()
member_instance = discord.Member(data=member_data, guild=guild_instance, state=state_mock)


class MockMember(CustomMockMixin, unittest.mock.Mock, ColourMixin, HashableMixin):
    """
    A Mock subclass to mock Member objects.

    Instances of this class will follow the specifications of `discord.Member` instances. For more
    information, see the `MockGuild` docstring.
    """

    spec_set = member_instance

    def __init__(self, roles: Optional[Iterable[MockRole]] = None, **kwargs) -> None:
        default_kwargs = {"name": "member", "id": next(self.discord_id), "bot": False, "pending": False}
        super().__init__(**collections.ChainMap(kwargs, default_kwargs))

        self.roles = [MockRole(name="@everyone", position=1, id=0)]
        if roles:
            self.roles.extend(roles)
        self.top_role = max(self.roles)

        if "mention" not in kwargs:
            self.mention = f"@{self.name}"


# Create a User instance to get a realistic Mock of `discord.User`
_user_data_mock = collections.defaultdict(unittest.mock.MagicMock, {"accent_color": 0})
user_instance = discord.User(
    data=unittest.mock.MagicMock(get=unittest.mock.Mock(side_effect=_user_data_mock.get)),
    state=unittest.mock.MagicMock(),
)


class MockUser(CustomMockMixin, unittest.mock.Mock, ColourMixin, HashableMixin):
    """
    A Mock subclass to mock User objects.

    Instances of this class will follow the specifications of `discord.User` instances. For more
    information, see the `MockGuild` docstring.
    """

    spec_set = user_instance

    def __init__(self, **kwargs) -> None:
        default_kwargs = {"name": "user", "id": next(self.discord_id), "bot": False}
        super().__init__(**collections.ChainMap(kwargs, default_kwargs))

        if "mention" not in kwargs:
            self.mention = f"@{self.name}"


# Create a User instance to get a realistic Mock of `discord.ClientUser`
_user_data_mock = collections.defaultdict(unittest.mock.MagicMock, {"accent_color": 0})
clientuser_instance = discord.ClientUser(
    data=unittest.mock.MagicMock(get=unittest.mock.Mock(side_effect=_user_data_mock.get)),
    state=unittest.mock.MagicMock(),
)


class MockClientUser(CustomMockMixin, unittest.mock.Mock, ColourMixin, HashableMixin):
    """
    A Mock subclass to mock ClientUser objects.

    Instances of this class will follow the specifications of `discord.ClientUser` instances. For more
    information, see the `MockGuild` docstring.
    """

    spec_set = clientuser_instance

    def __init__(self, **kwargs) -> None:
        default_kwargs = {"name": "user", "id": next(self.discord_id), "bot": True}
        super().__init__(**collections.ChainMap(kwargs, default_kwargs))

        if "mention" not in kwargs:
            self.mention = f"@{self.name}"


def _get_mock_loop() -> unittest.mock.Mock:
    """Return a mocked asyncio.AbstractEventLoop."""
    loop = unittest.mock.create_autospec(spec=asyncio.AbstractEventLoop, spec_set=True)

    # Since calling `create_task` on our MockBot does not actually schedule the coroutine object
    # as a task in the asyncio loop, this `side_effect` calls `close()` on the coroutine object
    # to prevent "has not been awaited"-warnings.
    def mock_create_task(coroutine, **kwargs):
        coroutine.close()
        return unittest.mock.Mock()

    loop.create_task.side_effect = mock_create_task

    return loop


class MockBot(CustomMockMixin, unittest.mock.MagicMock):
    """
    A MagicMock subclass to mock Bot objects.

    Instances of this class will follow the specifications of `discord.ext.commands.Bot` instances.
    For more information, see the `MockGuild` docstring.
    """

    spec_set = modmail.bot.ModmailBot(
        command_prefix=unittest.mock.MagicMock(),
        loop=_get_mock_loop(),
    )
    additional_spec_asyncs = ("wait_for", "redis_ready")

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.user = MockClientUser()

        self.loop = _get_mock_loop()
        self.http_session = unittest.mock.create_autospec(spec=aiohttp.ClientSession, spec_set=True)


# Create a TextChannel instance to get a realistic MagicMock of `discord.TextChannel`
channel_data = {
    "id": 1,
    "type": "TextChannel",
    "name": "channel",
    "parent_id": 1234567890,
    "topic": "topic",
    "position": 1,
    "nsfw": False,
    "last_message_id": 1,
}
state = unittest.mock.MagicMock()
guild = unittest.mock.MagicMock()
text_channel_instance = discord.TextChannel(state=state, guild=guild, data=channel_data)

channel_data["type"] = "VoiceChannel"
voice_channel_instance = discord.VoiceChannel(state=state, guild=guild, data=channel_data)


class MockTextChannel(CustomMockMixin, unittest.mock.Mock, HashableMixin):
    """
    A MagicMock subclass to mock TextChannel objects.

    Instances of this class will follow the specifications of `discord.TextChannel` instances. For
    more information, see the `MockGuild` docstring.
    """

    spec_set = text_channel_instance

    def __init__(self, **kwargs) -> None:
        default_kwargs = {"id": next(self.discord_id), "name": "channel", "guild": MockGuild()}
        super().__init__(**collections.ChainMap(kwargs, default_kwargs))

        if "mention" not in kwargs:
            self.mention = f"#{self.name}"


class MockVoiceChannel(CustomMockMixin, unittest.mock.Mock, HashableMixin):
    """
    A MagicMock subclass to mock VoiceChannel objects.

    Instances of this class will follow the specifications of `discord.VoiceChannel` instances. For
    more information, see the `MockGuild` docstring.
    """

    spec_set = voice_channel_instance

    def __init__(self, **kwargs) -> None:
        default_kwargs = {"id": next(self.discord_id), "name": "channel", "guild": MockGuild()}
        super().__init__(**collections.ChainMap(kwargs, default_kwargs))

        if "mention" not in kwargs:
            self.mention = f"#{self.name}"


# Create data for the DMChannel instance
state = unittest.mock.MagicMock()
me = unittest.mock.MagicMock()
dm_channel_data = {"id": 1, "recipients": [unittest.mock.MagicMock()]}
dm_channel_instance = discord.DMChannel(me=me, state=state, data=dm_channel_data)


class MockDMChannel(CustomMockMixin, unittest.mock.Mock, HashableMixin):
    """
    A MagicMock subclass to mock DMChannel objects.

    Instances of this class will follow the specifications of `discord.DMChannel` instances. For
    more information, see the `MockGuild` docstring.
    """

    spec_set = dm_channel_instance

    def __init__(self, **kwargs) -> None:
        default_kwargs = {"id": next(self.discord_id), "recipient": MockUser(), "me": MockUser()}
        super().__init__(**collections.ChainMap(kwargs, default_kwargs))


# Create CategoryChannel instance to get a realistic MagicMock of `discord.CategoryChannel`
category_channel_data = {
    "id": 1,
    "type": discord.ChannelType.category,
    "name": "category",
    "position": 1,
}

state = unittest.mock.MagicMock()
guild = unittest.mock.MagicMock()
category_channel_instance = discord.CategoryChannel(state=state, guild=guild, data=category_channel_data)


class MockCategoryChannel(CustomMockMixin, unittest.mock.Mock, HashableMixin):
    """
    A MagicMock subclass to mock CategoryChannel objects.

    Instances of this class will follow the specifications of `discord.CategoryChannel` instances. For
    more information, see the `MockGuild` docstring.
    """

    spec_set = category_channel_instance

    def __init__(self, **kwargs) -> None:
        default_kwargs = {"id": next(self.discord_id)}
        super().__init__(**collections.ChainMap(default_kwargs, kwargs))


# Create a thread instance to get a realistic MagicMock of `discord.Thread`
thread_metadata = {
    "archived": False,
    "archiver_id": None,
    "auto_archive_duration": 1440,
    "archive_timestamp": "2021-10-17T20:35:48.058121+00:00",
}
thread_data = {
    "id": "898070829617799179",
    "parent_id": "898070393619902544",
    "owner_id": "717983911824588862",
    "name": "user-0005",
    "type": discord.ChannelType.public_thread,
    "last_message_id": None,
    "message_count": 1,
    "member_count": 2,
    "thread_metadata": thread_metadata,
}

state = unittest.mock.MagicMock()
guild = unittest.mock.MagicMock()
thread_instance = discord.Thread(state=state, guild=guild, data=thread_data)


class MockThread(CustomMockMixin, unittest.mock.Mock, HashableMixin):
    """
    A MagicMock subclass to mock Thread objects.

    Instances of this class will follow the specifications of `discord.Thread` instances. For
    more information, see the `MockGuild` docstring.
    """

    spec_set = thread_instance

    def __init__(self, **kwargs) -> None:
        default_kwargs = {"id": next(self.discord_id)}
        super().__init__(**collections.ChainMap(default_kwargs, kwargs))


# Create a Message instance to get a realistic MagicMock of `discord.Message`
message_data = {
    "id": 1,
    "webhook_id": 898069816622067752,
    "attachments": [],
    "embeds": [],
    "application": "Discord Modmail",
    "activity": "mocking",
    "channel": unittest.mock.MagicMock(),
    "edited_timestamp": "2019-10-14T15:33:48+00:00",
    "type": "message",
    "pinned": False,
    "mention_everyone": False,
    "tts": None,
    "content": "content",
    "nonce": None,
}
state = unittest.mock.MagicMock()
channel = unittest.mock.MagicMock()
message_instance = discord.Message(state=state, channel=channel, data=message_data)


# Create a Context instance to get a realistic MagicMock of `discord.ext.commands.Context`
context_instance = Context(message=unittest.mock.MagicMock(), prefix="$", bot=MockBot(), view=None)
context_instance.invoked_from_error_handler = None


class MockContext(CustomMockMixin, unittest.mock.MagicMock):
    """
    A MagicMock subclass to mock Context objects.

    Instances of this class will follow the specifications of `discord.ext.commands.Context`
    instances. For more information, see the `MockGuild` docstring.
    """

    spec_set = context_instance

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.bot: MockBot = kwargs.get("bot", MockBot())
        self.guild: typing.Optional[MockGuild] = kwargs.get(
            "guild", MockGuild(me=MockMember(id=self.bot.user.id, bot=True))
        )
        self.author: typing.Union[MockMember, MockUser] = kwargs.get("author", MockMember())
        self.channel: typing.Union[MockTextChannel, MockThread, MockDMChannel] = kwargs.get(
            "channel", MockTextChannel(guild=self.guild)
        )
        self.message: MockMessage = kwargs.get(
            "message", MockMessage(author=self.author, channel=self.channel)
        )
        self.invoked_from_error_handler = kwargs.get("invoked_from_error_handler", False)

    @property
    def me(self) -> typing.Union[MockMember, MockClientUser]:
        """Similar to MockGuild.me except will return the class MockClientUser if guild is None."""
        # bot.user will never be None at this point.
        return self.guild.me if self.guild is not None else self.bot.user


attachment_instance = discord.Attachment(data=unittest.mock.MagicMock(id=1), state=unittest.mock.MagicMock())


class MockAttachment(CustomMockMixin, unittest.mock.MagicMock):
    """
    A MagicMock subclass to mock Attachment objects.

    Instances of this class will follow the specifications of `discord.Attachment` instances. For
    more information, see the `MockGuild` docstring.
    """

    spec_set = attachment_instance


class MockMessage(CustomMockMixin, unittest.mock.MagicMock):
    """
    A MagicMock subclass to mock Message objects.

    Instances of this class will follow the specifications of `discord.Message` instances. For more
    information, see the `MockGuild` docstring.
    """

    spec_set = message_instance

    def __init__(self, **kwargs) -> None:
        default_kwargs = {"attachments": []}
        super().__init__(**collections.ChainMap(kwargs, default_kwargs))
        self.author = kwargs.get("author", MockMember())
        self.channel = kwargs.get("channel", MockTextChannel())


emoji_data = {"require_colons": True, "managed": True, "id": 1, "name": "hyperlemon"}
emoji_instance = discord.Emoji(guild=MockGuild(), state=unittest.mock.MagicMock(), data=emoji_data)


class MockEmoji(CustomMockMixin, unittest.mock.MagicMock):
    """
    A MagicMock subclass to mock Emoji objects.

    Instances of this class will follow the specifications of `discord.Emoji` instances. For more
    information, see the `MockGuild` docstring.
    """

    spec_set = emoji_instance

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.guild = kwargs.get("guild", MockGuild())


partial_emoji_instance = discord.PartialEmoji(animated=False, name="guido")


class MockPartialEmoji(CustomMockMixin, unittest.mock.MagicMock):
    """
    A MagicMock subclass to mock PartialEmoji objects.

    Instances of this class will follow the specifications of `discord.PartialEmoji` instances. For
    more information, see the `MockGuild` docstring.
    """

    spec_set = partial_emoji_instance


reaction_instance = discord.Reaction(message=MockMessage(), data={"me": True}, emoji=MockEmoji())


class MockReaction(CustomMockMixin, unittest.mock.MagicMock):
    """
    A MagicMock subclass to mock Reaction objects.

    Instances of this class will follow the specifications of `discord.Reaction` instances. For
    more information, see the `MockGuild` docstring.
    """

    spec_set = reaction_instance

    def __init__(self, **kwargs) -> None:
        _users = kwargs.pop("users", [])
        super().__init__(**kwargs)
        self.emoji = kwargs.get("emoji", MockEmoji())
        self.message = kwargs.get("message", MockMessage())

        user_iterator = unittest.mock.AsyncMock()
        user_iterator.__aiter__.return_value = _users
        self.users.return_value = user_iterator

        self.__str__.return_value = str(self.emoji)


webhook_instance = discord.Webhook(data=unittest.mock.MagicMock(), session=unittest.mock.MagicMock())


class MockAsyncWebhook(CustomMockMixin, unittest.mock.MagicMock):
    """
    A MagicMock subclass to mock Webhook objects using an AsyncWebhookAdapter.

    Instances of this class will follow the specifications of `discord.Webhook` instances. For
    more information, see the `MockGuild` docstring.
    """

    spec_set = webhook_instance
    additional_spec_asyncs = ("send", "edit", "delete", "execute")
