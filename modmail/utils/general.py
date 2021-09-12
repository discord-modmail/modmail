import asyncio
from functools import wraps
from typing import Callable, Coroutine


CoroutineFunction = Callable[..., Coroutine]


def nonblocking(func: CoroutineFunction) -> CoroutineFunction:
    """
    Converts a coroutine into one that when awaited does not block.

    Note that the returned function now returns None, rather than returning the task.
    This is because it's intended for use with the priority dispatch, and tasks are "true"
    and would break that feature.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs) -> None:
        """Start a coroutine without blocking and triggering exceptions properly."""
        await_nonblocking(func(*args, **kwargs))

    return wrapper


def await_nonblocking(func: Coroutine) -> asyncio.Task:
    """Call a coroutine from potentially sync code without blocking, and ensure errors are reported."""
    task = asyncio.create_task(func)

    def ensure_exception(fut: asyncio.Future) -> None:
        """Ensure an exception in a task is raised without hard awaiting."""
        if fut.done() and not fut.cancelled():
            return
        fut.result()

    task.add_done_callback(ensure_exception)

    return task
