"""Execution handler base class."""

from __future__ import annotations

from abc import ABC, abstractmethod

from alphaagent.core.events import OrderEvent


class ExecutionHandler(ABC):
    """Consumes OrderEvents and produces FillEvents."""

    @abstractmethod
    def handle_order(self, event: OrderEvent) -> None: ...
