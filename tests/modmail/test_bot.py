"""
Test modmail basics.

- import module
- create a bot object
"""

import pytest

from modmail.bot import ModmailBot
from tests import mocks


@pytest.mark.dependency(name="create_bot")
@pytest.mark.asyncio
async def test_bot_creation() -> None:
    """Ensure we can make a ModmailBot instance."""
    bot = ModmailBot()
    # cleanup
    await bot.close()


@pytest.fixture
def bot() -> ModmailBot:
    """
    Pytest fixture.

    ModmailBot instance.
    """
    bot: ModmailBot = mocks.MockBot()
    return bot


@pytest.mark.dependency(depends=["create_bot"])
@pytest.mark.asyncio
async def test_bot_close(bot: ModmailBot) -> None:
    """Ensure bot closes without error."""
    import contextlib
    import io

    stdout = io.StringIO()
    with contextlib.redirect_stderr(stdout):
        await bot.close()
    resp = stdout.getvalue()
    assert resp == ""
