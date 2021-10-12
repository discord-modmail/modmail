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


def module_function_disidenticality(func1: Callable, func2: Callable) -> bool:
    """
    Determine if two functions are probably from the same module loaded twice.

    Returns true if:
    - same name
    - same qualname
    - same module path
    - but not the same function object

    This happens when a module is reloaded and old references are kept around.
    We unfortunately cannot compare the module object itself, as I don't know a
    way to access it from a function.

    This can also happen if someone is generating functions in a loop and not
    setting __name__ or __qualname__, but it's better practice to do that to
    name those appropriately.
    """
    return (
        func1.__qualname__ == func2.__qualname__
        and func1.__name__ == func2.__name__
        and func1.__module__ == func2.__module__
        and func1 != func2
    )
