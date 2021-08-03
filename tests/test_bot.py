import pytest

"""
Test modmail basics

- import module
- create a bot object
"""
from modmail.bot import ModmailBot


@pytest.mark.dependency(name="create_bot")
@pytest.mark.asyncio
async def test_bot_creation():
    """Create discord bot."""
    bot = ModmailBot()
    assert isinstance(bot, ModmailBot)

    # cleanup
    await bot.close()


@pytest.fixture
def bot() -> ModmailBot:
    """
    Pytest fixture.

    ModmailBot instance
    """
    bot: ModmailBot = ModmailBot()
    return bot


@pytest.mark.dependency(depends=["create_bot"])
@pytest.mark.asyncio
async def test_bot_aiohttp(bot):
    """Test aiohttp client session creates and closes without warnings."""
    import aiohttp

    await bot.create_session()
    assert isinstance(bot.http_session, aiohttp.ClientSession)
    await bot.close()


@pytest.mark.dependency(depends=["create_bot"])
@pytest.mark.asyncio
async def test_bot_close(bot):
    """Close bot."""
    import contextlib
    import io

    stdout = io.StringIO()
    with contextlib.redirect_stderr(stdout):
        await bot.close()
    resp = stdout.getvalue()
    assert resp == ""
