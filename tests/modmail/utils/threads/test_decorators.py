import pytest

from modmail.utils.threads import decorators
from tests import mocks


@pytest.fixture
def is_modmail_thread():
    """Fixture for is_modmail_thread of decorators to return the check it creates."""

    def func():
        pass

    check = decorators.is_modmail_thread()
    check(func)
    return func.__commands_checks__[-1]


def threaded_ctx(channel_id=None, /):
    """Return a ctx object from a thread with a parent channel property on the thread."""
    ctx = mocks.MockContext(channel=mocks.MockThread())
    ctx.channel.parent = mocks.MockTextChannel(id=channel_id or mocks.generate_realistic_id())
    return ctx


@pytest.mark.parametrize(
    ["ctx", "expected", "config_id"],
    [
        [threaded_ctx(42), True, 42],
        [threaded_ctx(42), False, 21],
        [mocks.MockContext(channel=mocks.MockTextChannel(id=1)), False, 123],
        [mocks.MockContext(channel=mocks.MockTextChannel(id=123)), False, 123],
    ],
)
def test_is_modmail_thread(ctx, is_modmail_thread, expected: bool, config_id: int):
    """Check that is_modmail_thread requires the channel to be a thread and with a parent of log channel."""
    ctx.bot.config.user.threads.relay_channel_id = config_id
    result = is_modmail_thread(ctx)

    assert expected == result
