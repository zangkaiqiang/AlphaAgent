"""Unit tests for the akshare-call retry helper (no network)."""

from __future__ import annotations

import pytest

from alphaagent.fundamentals.akshare_provider import _is_transient, _retry


def test_retry_succeeds_after_transient_failures():
    calls = {"n": 0}

    def producer():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("proxy dropped")
        return "ok"

    assert _retry(producer, attempts=3, base_delay=0) == "ok"
    assert calls["n"] == 3


def test_retry_reraises_last_transient_after_exhaustion():
    calls = {"n": 0}

    def producer():
        calls["n"] += 1
        raise ConnectionError("always down")

    with pytest.raises(ConnectionError):
        _retry(producer, attempts=3, base_delay=0)
    assert calls["n"] == 3  # tried exactly `attempts` times


def test_retry_does_not_retry_non_transient():
    calls = {"n": 0}

    def producer():
        calls["n"] += 1
        raise ValueError("bad data, not a network problem")

    with pytest.raises(ValueError):
        _retry(producer, attempts=3, base_delay=0)
    assert calls["n"] == 1  # raised immediately, no retry


def test_is_transient_classifies_proxy_error():
    import requests

    assert _is_transient(requests.exceptions.ProxyError("nope")) is True
    assert _is_transient(requests.exceptions.ConnectionError("nope")) is True
    assert _is_transient(ConnectionError("nope")) is True
    assert _is_transient(ValueError("nope")) is False
