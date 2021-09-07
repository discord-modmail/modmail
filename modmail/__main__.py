import asyncio
import logging

from modmail.bot import ModmailBot
from modmail.log import ModmailLogger
from modmail.utils.embeds import patch_embed


try:
    # noinspection PyUnresolvedReferences
    from colorama import init

    init()
except ImportError:
    pass


log: ModmailLogger = logging.getLogger(__name__)


def main() -> None:
    """Run the bot."""
    patch_embed()
    bot = ModmailBot()
    # Check if the database is alive before running the bot
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.init_db())
    bot.run(bot.config.bot.token)


if __name__ == "__main__":
    main()
