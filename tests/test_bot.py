"""
Test modmail basics.

- import module
- create a bot object
"""
import asyncio

import pytest

from modmail.bot import ModmailBot


@pytest.mark.dependency(name="create_bot")
@pytest.mark.asyncio
async def test_bot_creation():
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
    bot: ModmailBot = ModmailBot()
    return bot


@pytest.mark.dependency(depends=["create_bot"])
@pytest.mark.asyncio
async def test_bot_close(bot):
    """Ensure bot closes without error."""
    import contextlib
    import io

    stdout = io.StringIO()
    with contextlib.redirect_stderr(stdout):
        await bot.close()
    resp = stdout.getvalue()
    assert resp == ""


@pytest.mark.dependency(depends=["create_bot"])
def test_bot_main():
    """Import modmail.__main__."""
    from modmail.__main__ import main
