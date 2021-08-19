import asyncio
import logging
import signal
import typing as t

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


class ModmailBot(commands.Bot):
    """
    Base bot instance.

    Has an aiohttp.ClientSession and a ModmailConfig instance.
    """

    logger: ModmailLogger = logging.getLogger(__name__)

    def __init__(self, **kwargs):
        self.config = CONFIG
        self.start_time: t.Optional[arrow.Arrow] = None  # arrow.utcnow()
        super().__init__(
            **kwargs,
        )
        self.http_session: ClientSession = ClientSession(loop=self.loop)

    @classmethod
    def create(cls, *args, **kwargs) -> "ModmailBot":
        """
        Create a ModmailBot instance.

        This configures our instance with all of our custom options, without making __init__ unusable.
        """
        intents = Intents(
            guilds=True,
            messages=True,
            reactions=True,
            typing=True,
            members=True,
            emojis_and_stickers=True,
        )
        # start with an invisible status while we load everything
        status = discord.Status.invisible
        activity = Activity(type=discord.ActivityType.listening, name="users dming me!")
        # listen to messages mentioning the bot or matching the prefix
        # ! NOTE: This needs to use the configuration system to get the prefix from the db once it exists.
        prefix = commands.when_mentioned_or(CONFIG.bot.prefix)
        description = "Modmail bot by discord-modmail."
        # allow commands not caring of the case
        case_insensitive_commands = True
        # allow only user mentions by default.
        # ! NOTE: This may change in the future to allow roles as well
        allowed_mentions = AllowedMentions(everyone=False, users=True, roles=False, replied_user=True)
        return cls(
            case_insensitive=case_insensitive_commands,
            description=description,
            status=status,
            activity=activity,
            allowed_mentions=allowed_mentions,
            command_prefix=prefix,
            intents=intents,
            **kwargs,
        )

    def run(self, *args, **kwargs) -> None:
        """

        Start up our instance of the bot. Since this method is blocking, it must be called last.

        This method sets up the bot, loads extensions and plugins, and then executes the main task.

        A blocking call that abstracts away the event loop
        initialisation from you.
        If you want more control over the event loop then this
        function should not be used. Use :meth:`start` coroutine
        or :meth:`connect` + :meth:`login`.
        Roughly Equivalent to: ::
            try:
                loop.run_until_complete(start(*args, **kwargs))
            except KeyboardInterrupt:
                loop.run_until_complete(close())
                # cancel all tasks lingering
            finally:
                loop.close()
        .. warning::
            This function must be the last function to call due to the fact that it
            is blocking. That means that registration of events or anything being
            called after this function call will not execute until it returns.
        """
        loop = self.loop

        try:
            loop.add_signal_handler(signal.SIGINT, lambda: loop.stop())
            # this one we may want to get rid of, depending on certain things, and just hard stop instead.
            loop.add_signal_handler(signal.SIGTERM, lambda: loop.stop())
        except NotImplementedError:
            pass

        async def runner() -> None:
            try:
                # set start time to when we started the bot
                self.start_time = arrow.utcnow()
                # we want to load extensions before we log in, so that any issues in them are discovered
                # before we connect to discord
                self.load_extensions()
                # next, we log in to discord, to ensure that we are able to connect to discord
                await self.login(*args)
                # now that we're logged in and gotten a connection, we load all of the plugins
                self.load_plugins()
                # alert the user that we're done loading everything
                self.logger.notice("Loaded all extensions, and plugins. Starting bot.")
                # finally, we enter the main loop
                await self.connect(**kwargs)
            finally:
                if not self.is_closed():
                    await self.close()

        def stop_loop_on_completion(f) -> None:  # noqa: ANN001
            loop.stop()

        future = asyncio.ensure_future(runner(), loop=loop)
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

    async def on_ready(self) -> None:
        """Send basic login success message."""
        self.logger.info("Logged in as %s", self.user)
