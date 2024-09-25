import asyncio
import bisect
import inspect
import logging
from typing import Callable, Coroutine, Dict, List, Optional, Tuple, Union

from modmail.log import ModmailLogger
from modmail.utils.general import module_function_disidenticality


logger: ModmailLogger = logging.getLogger(__name__)

CoroutineFunction = Callable[..., Coroutine]

HANDLER_DISIDENTICALITY_WARNING = (
    "Event handler %r registered for event name '%s' a second time,"
    " but it is _not the same function_. Have you forgotten to add deregistration"
    " to cog_unload? By default I've deregistered the old handler to prevent duplication."
    " If you actually intend to register two functions with the same name from the same module,"
    " assign their __name__ and __qualname__ attributes so they are easily distinguishable."
)


class Dispatcher:
    """
    Dispatches events through an async event handler system.

    Supports blocking events and priority.
    """

    # These are separate because it makes using the bisect module easier. See _register_handler.
    blocking_handlers: Dict[str, List[CoroutineFunction]]
    blocking_priorities: Dict[str, List[int]]
    handlers: Dict[str, List[CoroutineFunction]]
    pending_handlers: Dict[Callable, List[Tuple[str, float]]]

    def __init__(self, *event_names: str):
        self.handlers = {}
        self.blocking_handlers = {}
        self.blocking_priorities = {}
        self.pending_handlers = {}

        self.register_events(*event_names)

    def register_events(self, *event_names: str) -> None:
        """
        Registers the given arguments as event types.

        This exists because if a user wants to dispatch or register a handler there is a
        significant possibility of typos. If we make event types manually registered, then we can
        fire a warning message in cases that are likely to be typos and make development
        significantly easier.
        """
        for event_name in event_names:
            if event_name in self.handlers:
                # Do not clear registers if a name is already registered
                continue
            self.handlers[event_name] = []
            self.blocking_handlers[event_name] = []
            self.blocking_priorities[event_name] = []

    def activate(self, instance: object) -> None:
        """
        Register all bound method handlers on a given class instance.

        Should be called during __init__.
        """
        for attr in dir(instance):
            value = getattr(instance, attr)
            if not callable(value):
                continue

            # Bound methods have __func__, which returns the actual function
            # we use that to determine which method was actually registered.
            if not hasattr(value, "__func__"):
                continue

            underlying_function = value.__func__

            if underlying_function not in self.pending_handlers:
                continue

            for (event_name, priority) in self.pending_handlers[underlying_function]:
                self._register_handler(event_name, priority, value)
            self.pending_handlers[underlying_function].clear()

    def deactivate(self, instance: object) -> None:
        """
        Unregister all bound method handlers on a given class instance.

        Should be called during __del__.
        """
        unregisterables = set()
        for attr in dir(instance):
            value = getattr(instance, attr)
            if not callable(value):
                continue

            # Bound methods have __func__, which returns the actual function
            # we use that to determine which method was actually registered.
            if not hasattr(value, "__func__"):
                continue

            underlying_function = value.__func__

            if underlying_function in self.pending_handlers:
                # Was never registered
                continue

            unregisterables.add(value)

        for event_name in self.handlers:
            for unregisterable in unregisterables.intersection(self.handlers[event_name]):
                self._remove_handler(unregisterable, event_name, False)

        for event_name in self.blocking_handlers:
            for unregisterable in unregisterables.intersection(self.blocking_handlers[event_name]):
                self._remove_handler(unregisterable, event_name, True)

    def _register_handler(
        self,
        event_name: Optional[str],
        priority: Optional[int],
        func: CoroutineFunction,
    ) -> None:
        """
        Actually register the handler.

        This function contains registration code, to keep it separate from the decorator code.
        """
        logger.debug("Registering %r to be called for event '%s', priority %s", func, event_name, priority)

        # This better fits under register(), but it'd be duped there.
        # This extracts the event name from the function name, formatted on_event_name, if it's not provided
        if not event_name:
            if func.__name__.startswith("on_"):
                event_name = func.__name__[3:]
            else:
                raise ValueError(
                    "You must pass an event name if the function name doesn't follow the on_eventname format."
                )

        # Check for `self` as first argument to tell if we're in a class
        # There unfortunately appears to be no better way to do this
        func_args = inspect.getfullargspec(func).args
        if func_args and func_args[0] == "self":
            if hasattr(func, "__self__") and func.__self__:
                # This is an already bound method
                in_class = False
            else:
                # This is an unbound class method
                in_class = True
        else:
            # This method doesn't have self, so it's probably not a class method
            # And this is the best we can do
            in_class = False

        if in_class:
            if func not in self.pending_handlers:
                self.pending_handlers[func] = []
            # We've been given an unbound method. We're registering on a class, so this will be re-called
            # later during __init__. We store all the event names it should be registered under on
            # in our pending_handlers for use at that time.
            self.pending_handlers[func].append((event_name, priority))
            return

        if event_name not in self.handlers:
            logger.warning(
                "event handler %r registered for event name '%s' that was not registered.",
                func,
                event_name,
            )
            self.handlers[event_name] = []
            self.blocking_handlers[event_name] = []
            self.blocking_priorities[event_name] = []

        # Nonblocking (gathered)
        if priority is None:
            if func in self.handlers[event_name]:
                logger.error(
                    "Event handler was already registered as async: handler %s, event name %s."
                    " Second registration ignored." % (func, event_name)
                )
                self._remove_handler(func, event_name, False)

            for handler in self.handlers[event_name]:
                if handler.__qualname__ == func.__qualname__:
                    if module_function_disidenticality(handler, func):
                        logger.warning(
                            HANDLER_DISIDENTICALITY_WARNING,
                            handler,
                            event_name,
                        )
                        self._remove_handler(handler, event_name, False)

            self.handlers[event_name].append(func)
            return

        # Blocking (run in sequence)
        for handler in self.blocking_handlers[event_name]:
            if handler.__qualname__ == func.__qualname__:
                if module_function_disidenticality(handler, func):
                    logger.warning(HANDLER_DISIDENTICALITY_WARNING, handler, event_name)

                    self._remove_handler(handler, event_name, True)

                if handler == func:
                    logger.error(
                        "Event handler was already registered as blocking: handler %s, event name %s."
                        " Second registration ignored." % (func, event_name)
                    )

                    self._remove_handler(handler, event_name, True)

        index = bisect.bisect_left(self.blocking_priorities[event_name], priority)
        self.blocking_priorities[event_name].insert(index, priority)
        self.blocking_handlers[event_name].insert(index, func)

    def register(
        self,
        event_name: Optional[str] = None,
        func: Optional[CoroutineFunction] = None,
        priority: Optional[int] = None,
    ) -> Union[CoroutineFunction, Callable]:
        """
        Register an event handler to be called when this event is dispatched.

        This can be used both as a raw call (`register("thread_create", priority=3)`)
         or as a decorator:
         @dispatcher.register("thread_create")
         def handle_new_threads(...

         If the event name is not provided, it is extracted from the method name similar to how dpy does it.

        Priority is optional. If provided, the handler will be called in order according to it's priority.
        If the handler returns True, the event is considered "handled" and further dispatch is cancelled.
        Lower numbers go first. Negative numbers are supported.

        If priority is not provided the event is dispatched asynchronously after all blocking handlers,
         and the return result of the handler has no effect.

        If you want priority and asynchronous dispatch, try using the `nonblocking` decorator from
         `modmail.utils.general`.
        """
        if func:
            self._register_handler(event_name, priority, func)
            return func

        def register_decorator(func: CoroutineFunction) -> CoroutineFunction:
            self._register_handler(event_name, priority, func)
            return func

        return register_decorator

    def unregister(self, func: CoroutineFunction, *event_names: Optional[str]) -> None:
        """
        Unregister a function from dispatch.

        If event_names is not provided, removes it from all handlers.
        If you have accidentally added a handler twice to an event, this will only remove one instance.
        """
        if not event_names:
            event_names = self.handlers.keys()

        for event_name in event_names:
            if event_name not in self.handlers:
                logger.exception(
                    "Attempted to unregister handler %r from event name %s, which wasn't registered.",
                    func,
                    event_name,
                )
                continue

            if func in self.handlers[event_name]:
                self._remove_handler(func, event_name, False)

            if func in self.blocking_handlers[event_name]:
                self._remove_handler(func, event_name, True)

    def _remove_handler(self, func: CoroutineFunction, event_name: str, blocking: bool = False) -> None:
        if blocking:
            # blocking handlers are two separate lists because it makes searching for items
            # (and thus bisect) a hundred times easier. But that does mean we have to keep them in sync.
            index = self.blocking_handlers[event_name].index(func)
            del self.blocking_handlers[event_name][index]
            del self.blocking_priorities[event_name][index]
        else:
            self.handlers[event_name].remove(func)

    async def dispatch(self, event_name: str, *args, **kwargs) -> None:
        """
        Trigger dispatch of an event, passing args directly to each handler.

        Beware passing mutable args--previous handlers, if misbehaving, can mutate them.
        """
        if event_name not in self.blocking_handlers:
            logger.exception(
                "Unregistered event '%s' was dispatched to no handlers with data: %r %r",
                event_name,
                args,
                kwargs,
            )
            self.blocking_handlers[event_name] = []
            self.handlers[event_name] = []
            self.blocking_priorities[event_name] = []

        for handler in self.blocking_handlers[event_name]:
            if await handler(*args, **kwargs):
                return

        await asyncio.gather(*(handler(*args, **kwargs) for handler in self.handlers[event_name]))
