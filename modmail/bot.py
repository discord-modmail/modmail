import logging
from contextlib import suppress
import discord
from aiohttp import ClientSession
from discord.ext import commands

from .config import CONFIG, INTERNAL

log = logging.getLogger(__name__)


class ModmailBot(commands.Bot):
    """
    Base bot instance.
    """

    def __init__(self, **kwargs):
        self.config = CONFIG
        self.internal = INTERNAL
        super().__init__(command_prefix=self.get_prefix, **kwargs)
        self.http_session = ClientSession()

    async def get_prefix(self, message=None):
        return [self.config.bot.prefix, f"<@{self.user.id}> ", f"<@!{self.user.id}> "]

    async def close(self) -> None:
        """
        Safely close HTTP session and extensions when bot is shutting down.
        """
        await super().close()

        for ext in list(self.extensions):
            try:
                self.unload_extension(ext)
            except Exception:
                log.error(f"Exception occured while unloading {ext.name}", exc_info=1)

        for cog in list(self.cogs):
            try:
                self.remove_cog(cog)
            except Exception:
                log.error(f"Exception occured while removing cog {cog.name}", exc_info=1)

        await super().close()

        if self.http_session:
            await self.http_session.close()

    def add_cog(self, cog: commands.Cog) -> None:
        """
        Delegate to super to register `cog`.
        This only serves to make the info log, so that extensions don't have to.
        """
        super().add_cog(cog)
        log.info(f"Cog loaded: {cog.qualified_name}")


bot = ModmailBot(intents=discord.Intents.all())
