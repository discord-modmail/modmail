import asyncio

import pytest

from modmail.utils.general import await_nonblocking, nonblocking


@pytest.mark.asyncio
async def test_await_nonblocking() -> None:
    """Ensure that we can execute coroutines asynchronously from a sync task."""
    a = 0

    async def test(number: int) -> None:
        nonlocal a
        a = number

    task = await_nonblocking(test(1))
    assert a == 0
    await task
    assert a == 1


@pytest.mark.asyncio
async def test_nonblocking_decorator() -> None:
    """
    Ensure the nonblocking decorator possesses nonblocking behavior.

    The sleeps are present to force asyncio to use a given resolution order for the
    asynchronous tasks, so we can clearly tell if they were executed parallel or sync.
    """
    a = 0

    @nonblocking
    async def test(number: int) -> None:
        nonlocal a
        await asyncio.sleep(0.05)
        a = number

    await test(1)
    assert a == 0
    await asyncio.sleep(0.1)
    assert a == 1
