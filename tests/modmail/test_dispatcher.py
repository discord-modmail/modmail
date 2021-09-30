from typing import Callable

import pytest

from modmail.dispatcher import Dispatcher


@pytest.fixture
def dispatcher() -> Dispatcher:
    """Ensure we can create a dispatcher."""
    return Dispatcher("member_leave")


def call_counter() -> Callable:
    """Generates a function that returns the number of times it was called."""
    tocks = 0

    def counter() -> int:
        nonlocal tocks
        tocks += 1
        return tocks

    return counter


def make_mock_handler() -> Callable:
    """Generates an async function that returns the number of times it was called."""
    tocks = 0

    async def mock_handler(*args) -> int:
        nonlocal tocks
        tocks += 1
        return tocks

    return mock_handler


@pytest.mark.dependency(name="register_thread_events")
def test_register_thread_create_event(dispatcher: Dispatcher) -> None:
    """Ensure registering events functions at all."""
    dispatcher.register_events("thread_create", "thread_close", "thread_message")


@pytest.mark.dependency(depends_on=["register_thread_events"])
def test_register_function_straight(dispatcher: Dispatcher) -> None:
    """Test the regular form of handler registration."""
    handler = make_mock_handler()

    dispatcher.register("thread_create", handler)


@pytest.mark.dependency(depends_on=["register_thread_events"])
@pytest.mark.asyncio
async def test_register_function_decorator(dispatcher: Dispatcher) -> None:
    """Test the decorator form of handler registration."""
    calls = 0

    @dispatcher.register("thread_create")
    async def mock_handler(*args):
        nonlocal calls
        calls += 1

    await dispatcher.dispatch("thread_create", False)

    assert calls == 1


@pytest.mark.dependency(depends_on=["register_thread_events"])
@pytest.mark.asyncio
async def test_register_function_deconame(dispatcher: Dispatcher) -> None:
    """Test that basic dispatch works."""
    calls = 0

    @dispatcher.register()
    async def on_thread_create(*args):
        nonlocal calls
        calls += 1

    await dispatcher.dispatch("thread_create", False)

    assert calls == 1


@pytest.mark.dependency(depends_on=["register_thread_events"])
@pytest.mark.asyncio
async def test_register_unregister(dispatcher: Dispatcher) -> None:
    """Test that unregistering prevents a handler from being called."""
    calls = 0

    @dispatcher.register()
    async def on_thread_create(*args):
        nonlocal calls
        calls += 1

    await dispatcher.dispatch("thread_create", False)

    assert calls == 1

    dispatcher.unregister(on_thread_create)

    await dispatcher.dispatch("thread_create", True)

    assert calls == 1


@pytest.mark.dependency(depends_on=["register_thread_events"])
@pytest.mark.asyncio
async def test_unregister_named(dispatcher: Dispatcher) -> None:
    """Test that we can unregister from only one name."""
    calls = 0

    @dispatcher.register()
    async def on_thread_create(*args):
        nonlocal calls
        calls += 1

    await dispatcher.dispatch("thread_create", False)

    assert calls == 1

    dispatcher.unregister(on_thread_create, "thread_message")

    await dispatcher.dispatch("thread_create", True)

    assert calls == 2

    dispatcher.unregister(on_thread_create, "thread_create")

    await dispatcher.dispatch("thread_create", True)

    assert calls == 2


@pytest.mark.dependency(depends_on=["register_thread_events"])
@pytest.mark.asyncio
async def test_priority_order(dispatcher: Dispatcher) -> None:
    """Test priority ordering and blocking of further event dispatch works.."""
    calls = 0

    @dispatcher.register()
    async def on_thread_create(*args) -> None:
        nonlocal calls
        calls += 1

    priority_calls = 0

    @dispatcher.register("thread_create", priority=3)
    async def priority_handler(*args) -> bool:
        nonlocal priority_calls
        priority_calls += 1
        return True

    await dispatcher.dispatch("thread_create", False)

    assert priority_calls == 1
    assert calls == 0

    high_priority_calls = 0

    @dispatcher.register("thread_create", priority=1)
    async def high_priority_handler(*args) -> bool:
        nonlocal high_priority_calls
        high_priority_calls += 1
        return False

    await dispatcher.dispatch("thread_create", False)

    assert priority_calls == 2
    assert calls == 0
    assert high_priority_calls == 1


@pytest.mark.dependency(depends_on=["register_thread_events"])
@pytest.mark.asyncio
async def test_bad_name_raises(dispatcher: Dispatcher) -> None:
    """Test that attempting to register a function without a clear event name fails."""
    with pytest.raises(ValueError):

        @dispatcher.register()
        async def bad_name(*args) -> None:
            pass


@pytest.mark.asyncio
async def test_unregister_priority(dispatcher: Dispatcher) -> None:
    """Test that priority events are successfully unregistered."""
    high_priority_calls = 0

    @dispatcher.register("thread_create", priority=1)
    async def high_priority_handler(*args) -> bool:
        nonlocal high_priority_calls
        high_priority_calls += 1
        return False

    await dispatcher.dispatch("thread_create", False)

    assert high_priority_calls == 1

    dispatcher.unregister(high_priority_handler)

    await dispatcher.dispatch("thread_create", False)

    assert high_priority_calls == 1


@pytest.mark.asyncio
async def test_bad_eventname_register_dispatch(dispatcher: Dispatcher) -> None:
    """Test that even unregistered events dispatch properly."""
    calls = 0

    @dispatcher.register()
    async def on_unnamed(*args) -> None:
        nonlocal calls
        calls += 1

    await dispatcher.dispatch("unnamed", False)

    assert calls == 1

    await dispatcher.dispatch("asdf")

    assert calls == 1


@pytest.mark.asyncio
async def test_class_dispatch() -> None:
    """Ensure the decorator works on class functions as well, and fires only for the instances."""

    class A:
        dispatcher = Dispatcher("class_test")

        def __init__(self):
            self.dispatcher.activate(self)

        async def fire(self) -> None:
            await self.dispatcher.dispatch("class_test", 2)

        @dispatcher.register("class_test")
        async def on_class_test(self, var1) -> None:
            assert var1 == 2

    assert A.dispatcher.handlers["class_test"] == []

    a = A()

    assert A.dispatcher.handlers["class_test"] == [a.on_class_test]

    await a.on_class_test(2)

    await a.fire()


@pytest.mark.asyncio
async def test_class_dispatch_latemethod() -> None:
    """Ensure we can register methods after class definition."""
    called = False

    class A:
        dispatcher = Dispatcher("class_test")

        def __init__(self):
            self.dispatcher.register_events("class_test")
            self.dispatcher.register("class_test", self.on_class_test)

        async def fire(self) -> None:
            await self.dispatcher.dispatch("class_test", 2)

        async def on_class_test(self, var1) -> None:
            nonlocal called
            called = True
            assert var1 == 2

    assert A.dispatcher.handlers["class_test"] == []

    a = A()

    assert A.dispatcher.handlers["class_test"] == [a.on_class_test]

    await a.fire()

    assert called
