import asyncio
import logging
import typing as t

import arrow
from aiohttp import ClientSession
from discord.ext import commands

from modmail.config import CONFIG
from modmail.log import ModmailLogger
from modmail.utils.extensions import EXTENSIONS, NO_UNLOAD, walk_extensions
from modmail.utils.plugins import PLUGINS, walk_plugins


class ModmailBot(commands.Bot):
    """
    Base bot instance.

    Has an aiohttp.ClientSession and a ModmailConfig instance.
    """

    main_task: asyncio.Task
    logger: ModmailLogger = logging.getLogger(__name__)

    def __init__(self, **kwargs):
        self.config = CONFIG
        self.http_session: t.Optional[ClientSession] = None
        self.start_time = arrow.utcnow()
        super().__init__(command_prefix=commands.when_mentioned_or(self.config.bot.prefix), **kwargs)

    async def create_session(self) -> None:
        """Create an aiohttp client session."""
        self.http_session = ClientSession()

    async def close(self) -> None:
        """Safely close HTTP session and unload plugins and extensions when bot is shutting down."""
        plugins = self.extensions & PLUGINS.keys()
        for plug in list(plugins):
            try:
                self.unload_extension(plug)
            except Exception:
                self.logger.error(f"Exception occured while unloading plugin {plug.name}", exc_info=True)

        for ext in list(self.extensions):
            try:
                self.unload_extension(ext)
            except Exception:
                self.logger.error(f"Exception occured while unloading {ext.name}", exc_info=True)

        for cog in list(self.cogs):
            try:
                self.remove_cog(cog)
            except Exception:
                self.logger.error(f"Exception occured while removing cog {cog.name}", exc_info=True)

        if self.http_session:
            await self.http_session.close()

        await super().close()

    def load_extensions(self) -> None:
        """Load all enabled extensions."""
        EXTENSIONS.update(walk_extensions())

        # set up no_unload global too
        for ext, value in EXTENSIONS.items():
            if value[1]:
                NO_UNLOAD.append(ext)

        for extension, value in EXTENSIONS.items():
            if value[0]:
                self.logger.debug(f"Loading extension {extension}")
                self.load_extension(extension)

    def load_plugins(self) -> None:
        """Load all enabled plugins."""
        PLUGINS.update(walk_plugins())

        for plugin, should_load in PLUGINS.items():
            if should_load:
                self.logger.debug(f"Loading plugin {plugin}")
                try:
                    # since we're loading user generated content,
                    # any errors here will take down the entire bot
                    self.load_extension(plugin)
                except Exception:
                    self.logger.error("Failed to load plugin {0}".format(plugin))

    def add_cog(self, cog: commands.Cog, *, override: bool = False) -> None:
        """
        Load a given cog.

        Utilizes the default discord.py loader beneath, but also checks so we can warn when we're
        loading a non-ModmailCog cog.
        """
        from modmail.utils.cogs import ModmailCog

        if not isinstance(cog, ModmailCog):
            self.logger.warning(
                f"Cog {cog.name} is not a ModmailCog. All loaded cogs should always be"
                f" instances of ModmailCog."
            )
        super().add_cog(cog, override=override)
        self.logger.info(f"Cog loaded: {cog.qualified_name}")

    def remove_cog(self, cog: str) -> None:
        """
        Delegate to super to unregister `cog`.

        This only serves to make the debug log, so that extensions don't have to.
        """
        super().remove_cog(cog)
        self.logger.info(f"Cog unloaded: {cog}")

    async def on_ready(self) -> None:
        """Send basic login success message."""
        self.logger.info("Logged in as %s", self.user)
