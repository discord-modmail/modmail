import typing as t

from discord.ext import commands
from discord.ext.commands import Context
from discord.threads import Thread


def is_thread_channel() -> t.Callable:
    """Check to see whether the channel in which the command is invoked is a discord thread or not."""

    async def predicate(ctx: Context) -> bool:
        if isinstance(ctx.channel, Thread):
            return True
        return False

    return commands.check(predicate)
