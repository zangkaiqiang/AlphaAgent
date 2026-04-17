from datetime import datetime

from alphaagent.core.event_bus import EventBus
from alphaagent.core.events import EventType, SignalEvent
from alphaagent.core.types import Side


def test_event_bus_dispatches_in_order():
    bus = EventBus()
    received = []
    bus.subscribe(EventType.SIGNAL, lambda e: received.append(e.symbol))

    for sym in ["600000", "000001", "600519"]:
        bus.put(SignalEvent(timestamp=datetime(2023, 1, 1), symbol=sym, side=Side.BUY))

    bus.dispatch()
    assert received == ["600000", "000001", "600519"]


def test_event_bus_handlers_can_enqueue_more_events():
    bus = EventBus()
    log = []

    def on_signal(e):
        log.append(("signal", e.symbol))
        if e.symbol == "a":
            bus.put(SignalEvent(timestamp=e.timestamp, symbol="b", side=Side.BUY))

    bus.subscribe(EventType.SIGNAL, on_signal)
    bus.put(SignalEvent(timestamp=datetime(2023, 1, 1), symbol="a", side=Side.BUY))
    bus.dispatch()

    assert log == [("signal", "a"), ("signal", "b")]
