import asyncio
from functools import wraps
from typing import Callable, Coroutine

CoroutineFunction = Callable[..., Coroutine]


def nonblocking(func: CoroutineFunction) -> CoroutineFunction:
    """Converts a coroutine into one that when awaited does not block."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        """Start a coroutine without blocking and triggering exceptions properly."""
        task = asyncio.create_task(func(*args, **kwargs))

        def ensure_exception(fut: asyncio.Future) -> None:
            """Ensure an exception in a task is raised without hard awaiting."""
            if fut.done() and not fut.cancelled():
                return
            fut.result()

        task.add_done_callback(ensure_exception)

    return wrapper
