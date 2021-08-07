import logging

try:
    # noinspection PyUnresolvedReferences
    from colorama import init

    init()
except ImportError:
    pass

from modmail.bot import ModmailBot

log = logging.getLogger(__name__)


def main() -> None:
    """Run the bot."""
    bot = ModmailBot()
    bot.load_extensions()
    bot.load_plugins()
    log.notice("Running the bot.")
    bot.run(bot.config.bot.token)


if __name__ == "__main__":
    main()
