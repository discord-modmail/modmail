import logging

try:
    # noinspection PyUnresolvedReferences
    from colorama import init

    init()
except ImportError:
    pass

from .bot import ModmailBot

log = logging.getLogger(__name__)


def main() -> None:
    """Run the bot."""
    bot = ModmailBot()
    log.notice("running bot")
    bot.run(bot.config.bot.token)


if __name__ == "__main__":
    main()
