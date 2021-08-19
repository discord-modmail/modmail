import logging

from modmail.bot import ModmailBot
from modmail.log import ModmailLogger

try:
    # noinspection PyUnresolvedReferences
    from colorama import init

    init()
except ImportError:
    pass


log: ModmailLogger = logging.getLogger(__name__)


def main() -> None:
    """Run the bot."""
    bot = ModmailBot.create()
    bot.run(bot.config.bot.token)


if __name__ == "__main__":
    main()
