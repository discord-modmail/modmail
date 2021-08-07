import asyncio
import logging

import arrow
from aiohttp import ClientSession
from discord.ext import commands

from modmail.config import CONFIG, INTERNAL

log = logging.getLogger(__name__)


class ModmailBot(commands.Bot):
    """
    Base bot instance.

    Has an aiohttp.ClientSession and a ModmailConfig instance.
    """

    main_task: asyncio.Task

    def __init__(self, **kwargs):
        self.config = CONFIG
        self.internal = INTERNAL
        self.http_session: ClientSession = None
        self.start_time = arrow.utcnow()
        super().__init__(command_prefix=commands.when_mentioned_or(self.config.bot.prefix), **kwargs)

    async def create_session(self) -> None:
        """Create an aiohttp client session."""
        self.http_session = ClientSession()

    async def close(self) -> None:
        """Safely close HTTP session and extensions when bot is shutting down."""
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

        if self.http_session:
            await self.http_session.close()

        await super().close()

    def load_extensions(self) -> None:
        """Load all enabled extensions."""
        # Must be done here to avoid a circular import.
        from modmail.utils.extensions import EXTENSIONS, walk_extensions

        EXTENSIONS.update(walk_extensions())
        for extension, should_load in EXTENSIONS.items():
            if should_load:
                self.load_extension(extension)

    def add_cog(self, cog: commands.Cog) -> None:
        """
        Delegate to super to register `cog`.

        This only serves to make the info log, so that extensions don't have to.
        """
        super().add_cog(cog)
        log.info(f"Cog loaded: {cog.qualified_name}")

    def remove_cog(self, cog: commands.Cog) -> None:
        """
        Delegate to super to unregister `cog`.

        This only serves to make the debug log, so that extensions don't have to.
        """
        super().remove_cog(cog)
        log.trace(f"Cog unloaded: {cog}")

    async def on_ready(self) -> None:
        """Send basic login success message."""
        log.info("Logged in as %s", self.user)
