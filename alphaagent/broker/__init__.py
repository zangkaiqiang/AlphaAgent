"""Broker adapters. Paper for safe live-like testing, QMT for real A-share trading."""

from alphaagent.broker.base import Broker, BrokerError
from alphaagent.broker.paper import PaperBroker

__all__ = ["Broker", "BrokerError", "PaperBroker"]


def qmt_broker(*args, **kwargs):
    """Lazy QMT factory so ``xtquant`` only imports when actually used."""
    from alphaagent.broker.qmt import QMTBroker

    return QMTBroker(*args, **kwargs)
