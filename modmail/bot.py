import asyncio
import logging
import signal
import socket
from typing import Any, Optional, Set

import aiohttp
import arrow
import discord
from discord import Activity, AllowedMentions, Intents
from discord.client import _cleanup_loop
from discord.ext import commands

from modmail.addons.errors import NoPluginTomlFoundError
from modmail.addons.models import Plugin
from modmail.addons.plugins import PLUGINS, find_plugins
from modmail.config import CONFIG
from modmail.dispatcher import Dispatcher
from modmail.log import ModmailLogger
from modmail.utils.cogs import ModmailCog
from modmail.utils.extensions import BOT_MODE, EXTENSIONS, NO_UNLOAD, walk_extensions


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
    mode: int
    dispatcher: Dispatcher

    def __init__(self, **kwargs):
        self.config = CONFIG
        self.start_time: Optional[arrow.Arrow] = None  # arrow.utcnow()
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.dispatcher = Dispatcher()

        self._connector = None
        self._resolver = None

        # keys: plugins, list values: all plugin files
        self.installed_plugins: Optional[Set[Plugin]] = None

        status = discord.Status.online
        activity = Activity(type=discord.ActivityType.listening, name="users dming me!")
        # listen to messages mentioning the bot or matching the prefix
        # ! NOTE: This needs to use the configuration system to get the prefix from the db once it exists.
        prefix = commands.when_mentioned_or(CONFIG.bot.prefix)
        # allow only user mentions by default.
        # ! NOTE: This may change in the future to allow roles as well
        allowed_mentions = AllowedMentions(everyone=False, users=True, roles=False, replied_user=True)
        # override passed kwargs if they are None
        kwargs["case_insensitive"] = kwargs.get("case_insensitive", True)
        # do not let the description be overridden.
        kwargs["description"] = "Modmail bot by discord-modmail."
        kwargs["status"] = kwargs.get("status", status)
        kwargs["activity"] = kwargs.get("activity", activity)
        kwargs["allowed_mentions"] = kwargs.get("allowed_mentions", allowed_mentions)
        kwargs["command_prefix"] = kwargs.get("command_prefix", prefix)
        kwargs["intents"] = kwargs.get("intents", REQUIRED_INTENTS)
        super().__init__(
            **kwargs,
        )

    async def create_connectors(self, *args, **kwargs) -> None:
        """Re-create the connector and set up sessions before logging into Discord."""
        # Use asyncio for DNS resolution instead of threads so threads aren't spammed.
        self._resolver = aiohttp.AsyncResolver()

        # Use AF_INET as its socket family to prevent HTTPS related problems both locally
        # and in production.
        self._connector = aiohttp.TCPConnector(
            resolver=self._resolver,
            family=socket.AF_INET,
        )

        # Client.login() will call HTTPClient.static_login() which will create a session using
        # this connector attribute.
        self.http.connector = self._connector

        self.http_session = aiohttp.ClientSession(connector=self._connector)

    async def start(self, token: str, reconnect: bool = True) -> None:
        """
        Start the bot.

        This function is called by the run method, and finishes the set up of the bot that needs an
        asyncrhonous event loop running, before connecting the bot to discord.
        """
        try:
            # create the aiohttp session
            await self.create_connectors()
            self.logger.trace("Created aiohttp.ClientSession.")
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
        plugins = []
        for plug in PLUGINS:
            plugins.extend([mod for mod in plug.modules])

        plugins = self.extensions.keys() & plugins

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

        await super().close()

        if self.http_session:
            await self.http_session.close()

        if self._connector:
            await self._connector.close()

        if self._resolver:
            await self._resolver.close()

    def load_extensions(self) -> None:
        """Load all enabled extensions."""
        self.mode = BOT_MODE
        EXTENSIONS.update(walk_extensions())

        for ext, metadata in EXTENSIONS.items():
            # set up no_unload global too
            if metadata.no_unload:
                NO_UNLOAD.append(ext)

            if metadata.load_if_mode & BOT_MODE:
                self.logger.info(f"Loading extension {ext}")
                self.load_extension(ext)
            else:
                self.logger.debug(f"SKIPPING load of extension {ext} due to BOT_MODE.")

    def load_plugins(self) -> None:
        """Load all enabled plugins."""
        self.installed_plugins = PLUGINS
        dont_load_at_start = []
        try:
            PLUGINS.update(find_plugins())
        except NoPluginTomlFoundError:
            # no local plugins
            pass
        else:
            for plug in self.installed_plugins:
                if plug.enabled:
                    continue
                self.logger.debug(f"Not loading {plug.__str__()} on start since it's not enabled.")
                dont_load_at_start.extend(plug.modules)

        for plug in PLUGINS:
            for mod, metadata in plug.modules.items():
                if metadata.load_if_mode & self.mode and mod not in dont_load_at_start:
                    self.logger.debug(f"Loading plugin {mod}")
                    try:
                        # since we're loading user generated content,
                        # any errors here will take down the entire bot
                        self.load_extension(mod)
                    except Exception:
                        self.logger.error(f"Failed to load plugin {mod!s}", exc_info=True)
                else:
                    self.logger.debug(f"SKIPPED loading plugin {mod}")

    def add_cog(self, cog: commands.Cog, *, override: bool = False) -> None:
        """
        Load a given cog.

        Utilizes the default discord.py loader beneath, but also checks so we can warn when we're
        loading a non-ModmailCog cog.
        """
        if not isinstance(cog, ModmailCog):
            self.logger.warning(
                f"Cog {cog.qualified_name} is not a ModmailCog. All loaded cogs should always be"
                " instances of ModmailCog."
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

    async def on_ready(self) -> None:
        """Send basic login success message."""
        self.logger.info("Logged in as %s", self.user)
