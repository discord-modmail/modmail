from typing import Callable

from discord.ext import commands
from discord.ext.commands import Context
from discord.threads import Thread


class ThreadException(Exception):  # noqa: N818
    """The base error for threads, all threads errors should inherit from this exception."""

    pass


class ThreadNotFoundError(ThreadException):
    """Raised when a thread is not found."""

    pass


class ThreadAlreadyExistsError(ThreadException):
    """Raised when a thread already exists."""

    pass


def is_modmail_thread() -> Callable:
    """Check to see whether the channel in which the command is invoked is a discord thread or not."""

    def check(ctx: Context) -> bool:
        """
        Check contextual channel is a modmail thread channel.

        All modmail thread channels are a thread, so if it isn't we know we can stop checking at that point.
        If it is a thread channel, then we also know it must have a parent attribute, so we can safely
        check if the id is the same as the configured thread log channel id.
        """
        return (
            isinstance(ctx.channel, Thread)
            and ctx.channel.parent.id == ctx.bot.config.thread.relay_channel_id
        )

    return commands.check(check)
