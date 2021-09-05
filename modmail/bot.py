import asyncio
import logging
import signal
import typing as t
from typing import Any

import arrow
import discord
from aiohttp import ClientSession
from discord import Activity, AllowedMentions, Intents
from discord.client import _cleanup_loop
from discord.ext import commands

from modmail.config import CONFIG
from modmail.log import ModmailLogger
from modmail.utils.extensions import EXTENSIONS, NO_UNLOAD, walk_extensions
from modmail.utils.plugins import PLUGINS, walk_plugins
from modmail.utils.threads import Ticket


REQUIRED_INTENTS = Intents(
    guilds=True,
    messages=True,
    reactions=True,
    typing=True,
    members=True,
    emojis_and_stickers=True,
)


class ModmailBot(commands.Bot):
    """
    Base bot instance.

    Has an aiohttp.ClientSession and a ModmailConfig instance.
    """

    logger: ModmailLogger = logging.getLogger(__name__)
    tickets: t.Dict[int, Ticket] = dict()

    def __init__(self, **kwargs):
        self.config = CONFIG
        self.start_time: t.Optional[arrow.Arrow] = None  # arrow.utcnow()
        self.http_session: t.Optional[ClientSession] = None
        self._guild_available = asyncio.Event()
        self.start_time = arrow.utcnow()

        status = discord.Status.online
        activity = Activity(type=discord.ActivityType.listening, name="users dming me!")
        # listen to messages mentioning the bot or matching the prefix
        # ! NOTE: This needs to use the configuration system to get the prefix from the db once it exists.
        prefix = commands.when_mentioned_or(CONFIG.bot.prefix)
        # allow only user mentions by default.
        # ! NOTE: This may change in the future to allow roles as well
        allowed_mentions = AllowedMentions(everyone=False, users=True, roles=False, replied_user=True)
        super().__init__(
            case_insensitive=True,
            description="Modmail bot by discord-modmail.",
            status=status,
            activity=activity,
            allowed_mentions=allowed_mentions,
            command_prefix=prefix,
            intents=REQUIRED_INTENTS,
            **kwargs,
        )

    async def start(self, token: str, reconnect: bool = True) -> None:
        """
        Start the bot.

        This function is called by the run method, and finishes the set up of the bot that needs an
        asyncrhonous event loop running, before connecting the bot to discord.
        """
        try:
            # create the aiohttp session
            self.http_session = ClientSession(loop=self.loop)
            self.logger.trace("Created ClientSession.")
            # set start time to when we started the bot.
            # This is now, since we're about to connect to the gateway.
            # This should also be before we load any extensions, since if they have a load time, it should
            # be after the bot start time.
            self.start_time = arrow.utcnow()
            # we want to load extensions before we log in, so that any issues in them are discovered
            # before we connect to discord. This keeps us from connecting to the gateway a lot if we have a
            # problem with an extension.
            self.load_extensions()
            # next, we log in to discord, to ensure that we are able to connect to discord
            # This only logs in to discord and gets a gateway, it does not connect to the websocket
            await self.login(token)
            # now that we're logged in and ensured we can have connection, we load all of the plugins
            # The reason to wait until we know we have a gateway we can connect to, even though we have not
            # signed in yet, is in some cases, a plugin may be poorly made and mess up if it is loaded but
            # the bot never connects to discord. Putting this below the login ensures that we don't load if
            # we don't have a gateway.
            self.load_plugins()
            # alert the user that we're done loading everything
            self.logger.notice("Loaded all extensions, and plugins. Starting bot.")
            # finally, we enter the main loop
            await self.connect(reconnect=reconnect)
        finally:
            if not self.is_closed():
                await self.close()

    def run(self, *args, **kwargs) -> None:
        """

        Start up our instance of the bot. Since this method is blocking, it must be called last.

        This method does several things, it loads extensions and plugins,
        and then executes the main task.

        This method was copied from discord.py and modified to suit our needs.
        """
        loop = self.loop

        try:
            # adds signal handlers so the loop is safely stopped
            loop.add_signal_handler(signal.SIGINT, lambda: loop.stop())
            # this one we may want to get rid of, depending on certain things, and just hard stop instead.
            loop.add_signal_handler(signal.SIGTERM, lambda: loop.stop())
        except NotImplementedError:
            pass

        def stop_loop_on_completion(f: Any) -> None:
            loop.stop()

        future = asyncio.ensure_future(self.start(*args, **kwargs), loop=loop)
        future.add_done_callback(stop_loop_on_completion)
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            self.logger.info("Received signal to terminate bot and event loop.")
        finally:
            future.remove_done_callback(stop_loop_on_completion)
            self.logger.info("Cleaning up tasks.")
            _cleanup_loop(loop)

        if not future.cancelled():
            try:
                return future.result()
            except KeyboardInterrupt:
                # I am unsure why this gets raised here but suppress it anyway
                return None

    async def close(self) -> None:
        """Safely close HTTP session, unload plugins and extensions when the bot is shutting down."""
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
                    self.logger.error("Failed to load plugin {0}".format(plugin), exc_info=True)

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

        This only serves to make the info log, so that extensions don't have to.
        """
        super().remove_cog(cog)
        self.logger.info(f"Cog unloaded: {cog}")

    async def on_guild_available(self, guild: discord.Guild) -> None:
        """
        Set the internal guild available event when constants.Guild.id becomes available.

        If the cache appears to still be empty (no members, no channels, or no roles), the event
        will not be set.
        """
        if guild.id != self.config.bot.guild_id:
            return

        if not guild.roles or not guild.members or not guild.channels:
            msg = "Guild available event was dispatched but the cache appears to still be empty!"
            self.logger.warning(msg)

            return

        self._guild_available.set()

    async def on_guild_unavailable(self, guild: discord.Guild) -> None:
        """Clear the internal guild available event when constants.Guild.id becomes unavailable."""
        if guild.id != self.config.bot.guild_id:
            return

        self._guild_available.clear()

    async def wait_until_guild_available(self) -> None:
        """
        Wait until the constants.Guild.id guild is available (and the cache is ready).

        The on_ready event is inadequate because it only waits 2 seconds for a GUILD_CREATE
        gateway event before giving up and thus not populating the cache for unavailable guilds.
        """
        await self._guild_available.wait()

    async def on_ready(self) -> None:
        """Send basic login success message."""
        self.logger.info("Logged in as %s", self.user)
