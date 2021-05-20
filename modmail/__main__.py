import asyncio
import logging
import sys

import discord

try:
    # noinspection PyUnresolvedReferences
    from colorama import init

    init()
except ImportError:
    pass

from .bot import ModmailBot

log = logging.getLogger(__name__)


def main():
    """Run the bot."""
    # try:
    #     # noinspection PyUnresolvedReferences
    #     import uvloop

    #     log.debug("Setting up with uvloop.")
    #     uvloop.install()
    # except ImportError:
    #     log.debug("UV loop not installed. Skipping.")
    #     pass

    bot = ModmailBot()
    log.notice('running bot')
    bot.run(bot.config.bot.token)


if __name__ == "__main__":
    main()
