from __future__ import annotations

import re as _re
from collections.abc import Mapping

from . import mcp_response as _mcp_response
from .http_client import get_json, status_timeout


def _active_filename() -> str:
    """Return the currently active filename as known by the server."""
    try:
        st = get_json("status", timeout=status_timeout())
        if isinstance(st, dict) and st.get("filename"):
            return str(st.get("filename"))
    except Exception:
        pass
    return "(none)"


def _mcp_result(*, ok: bool, file: str | None = None, **payload: object) -> dict:
    return _mcp_response.mcp_result(ok=ok, file=file or _active_filename(), **payload)


def _mcp_from_json(
    data: object,
    *,
    file: str | None = None,
    request_info: object | None = None,
    **payload: object,
) -> dict:
    return _mcp_response.mcp_from_json(
        data,
        file=file or _active_filename(),
        request_info=request_info,
        **payload,
    )


def _mcp_from_text(
    text: str | None, *, file: str | None = None, key: str = "text", **payload: object
) -> dict:
    return _mcp_response.mcp_from_text(
        text,
        file=file or _active_filename(),
        key=key,
        **payload,
    )


def _mcp_from_list(
    items: list | None, *, file: str | None = None, key: str = "items", **payload: object
) -> dict:
    return _mcp_response.mcp_from_list(
        items,
        file=file or _active_filename(),
        key=key,
        **payload,
    )


def _fetch_paginated_list(
    endpoint: str,
    *,
    file: str,
    offset: int,
    limit: int,
    result_key: str,
    params: Mapping[str, object] | None = None,
    timeout: float | None = None,
    extra_payload: dict[str, object] | None = None,
) -> dict:
    query: dict[str, object] = {"offset": offset, "limit": limit}
    if params:
        query.update(params)
    data = get_json(endpoint, query, timeout=timeout)
    if isinstance(data, dict) and "error" not in data:
        payload = {result_key: data.get(result_key, []) or []}
        if extra_payload:
            payload.update(extra_payload)
        return _mcp_result(ok=True, file=file, offset=offset, limit=limit, **payload)
    return _mcp_from_json(data, file=file, **query)


def _is_int_like(text: str) -> bool:
    """Best-effort integer detection for routing params (name vs address)."""
    s = (text or "").strip()
    if not s:
        return False
    if s[0] in "+-":
        s = s[1:].strip()
    if not s:
        return False

    lowered = s.lower()
    if lowered.startswith(("dec:", "decimal:", "d:")):
        body = s.split(":", 1)[1].strip()
        return _re.fullmatch(r"[0-9_]+", body) is not None

    if lowered.startswith(("hex:", "h:")):
        body = s.split(":", 1)[1].strip()
        return _re.fullmatch(r"[0-9a-fA-F_]+", body) is not None

    if lowered.startswith("0x"):
        return _re.fullmatch(r"[0-9a-fA-F_]+", s[2:]) is not None
    if lowered.startswith("0b"):
        return _re.fullmatch(r"[01_]+", s[2:]) is not None
    if lowered.startswith("0o"):
        return _re.fullmatch(r"[0-7_]+", s[2:]) is not None

    if lowered.endswith("h") and _re.fullmatch(r"[0-9a-f_]+h", lowered):
        return True

    if _re.fullmatch(r"[0-9_]+", s):
        return True
    if _re.fullmatch(r"[0-9a-fA-F_]+", s):
        return True

    return False


__all__ = [
    "_active_filename",
    "_fetch_paginated_list",
    "_is_int_like",
    "_mcp_from_json",
    "_mcp_from_list",
    "_mcp_from_text",
    "_mcp_result",
]
