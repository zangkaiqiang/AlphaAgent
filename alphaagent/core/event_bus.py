"""Simple in-process event bus with FIFO queue + typed subscribers."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable
from typing import TypeVar

from alphaagent.core.events import Event, EventType

Handler = Callable[[Event], None]
E = TypeVar("E", bound=Event)


class EventBus:
    """Synchronous event bus.

    Producers call ``put()``; ``dispatch()`` drains the queue and fans out to
    subscribers registered via ``subscribe()``. Handlers may enqueue further
    events (e.g. Signal -> Order -> Fill), which are processed in order.
    """

    def __init__(self) -> None:
        self._queue: deque[Event] = deque()
        self._handlers: dict[EventType, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: EventType, handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    def put(self, event: Event) -> None:
        self._queue.append(event)

    def dispatch(self) -> int:
        """Drain the queue. Returns number of events dispatched."""
        count = 0
        while self._queue:
            event = self._queue.popleft()
            for handler in self._handlers.get(event.type, ()):
                handler(event)
            count += 1
        return count

    def clear(self) -> None:
        self._queue.clear()

    def __len__(self) -> int:
        return len(self._queue)
