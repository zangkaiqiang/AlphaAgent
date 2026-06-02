"""Response envelope helpers.

The API contract wraps every response as ``{ "data": ..., "error": null }``
on success and ``{ "data": null, "error": { code, message } }`` on failure.
"""

from __future__ import annotations

from typing import Any


def ok(data: Any) -> dict[str, Any]:
    return {"data": data, "error": None}


def err(code: str, message: str) -> dict[str, Any]:
    return {"data": None, "error": {"code": code, "message": message}}
