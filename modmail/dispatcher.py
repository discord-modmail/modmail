import asyncio
import bisect
import logging
from typing import Callable, Coroutine, Dict, List, Optional, Union

from modmail import ModmailLogger

logger: ModmailLogger = logging.getLogger(__name__)

CoroutineFunction = Callable[..., Coroutine]


class Dispatcher:
    """
    Dispatches events through an async event handler system.

    Supports blocking events and priority.
    """

    # These are separate because it makes using the bisect module easier. See _register_handler.
    blocking_handlers: Dict[str, List[CoroutineFunction]]
    blocking_priorities: Dict[str, List[int]]
    handlers: Dict[str, List[CoroutineFunction]]

    def __init__(self, *event_names: str):
        self.handlers = {}
        self.blocking_handlers = {}
        self.blocking_priorities = {}

        self.register_events(*event_names)

    def register_events(self, *event_names: str) -> None:
        """
        Registers the given arguments as event types.

        This exists because if a user wants to dispatch or register a handler there is a  or
        significant possibility of typos. If we make event types manually registered, then we can
        fire a warning message in cases that are likely to be typos and make development
        significantly easier.
        """
        for event_name in event_names:
            self.handlers[event_name] = []
            self.blocking_handlers[event_name] = []
            self.blocking_priorities[event_name] = []

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

        if event_name not in self.handlers:
            logger.warning(
                "Warning: event handler %r registered for event name '%s' that was not registered.",
                func,
                event_name,
            )
            self.handlers[event_name] = []
            self.blocking_handlers[event_name] = []
            self.blocking_priorities[event_name] = []

        if priority is None:
            self.handlers[event_name].append(func)
        else:
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
                self.handlers[event_name].remove(func)

            if func in self.blocking_handlers[event_name]:
                # blocking handlers are two separate lists because it makes searching for items
                # (and thus bisect) a hundred times easier. But that does mean we have to keep them in sync.
                index = self.blocking_handlers[event_name].index(func)
                del self.blocking_handlers[event_name][index]
                del self.blocking_priorities[event_name][index]

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
