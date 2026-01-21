from __future__ import annotations


def mcp_result(*, ok: bool, file: str | None = None, **payload: object) -> dict[str, object]:
    """Standard MCP tool response envelope."""
    out: dict[str, object] = {"ok": ok, **payload}
    out.setdefault("file", file)
    return out


def mcp_from_json(
    data: object,
    *,
    file: str | None = None,
    request_info: object | None = None,
    **payload: object,
) -> dict[str, object]:
    request_context: object | None
    if request_info is not None:
        request_context = request_info
    elif payload:
        request_context = dict(payload)
    else:
        request_context = None

    if data is None:
        out: dict[str, object] = {"error": "No response from server"}
        if request_context is not None:
            out["request"] = request_context
        return mcp_result(ok=False, file=file, **out)

    if isinstance(data, dict):
        if "error" in data:
            ok = False
        elif isinstance(data.get("success"), bool):
            ok = bool(data.get("success"))
        else:
            ok = True

        out = dict(data)
        out.pop("ok", None)
        out.pop("file", None)

        if not ok and request_context is not None:
            out["request"] = request_context

        return mcp_result(ok=ok, file=file, **out)

    return mcp_result(ok=True, file=file, raw=data)


def mcp_from_text(
    text: str | None,
    *,
    file: str | None = None,
    key: str = "text",
    **payload: object,
) -> dict[str, object]:
    if text is None:
        return mcp_result(ok=False, file=file, error="No response from server", **payload)
    stripped = str(text).strip()
    if stripped.startswith(("Error ", "Request failed")):
        return mcp_result(ok=False, file=file, error=stripped, **payload)

    merged = dict(payload)
    merged[key] = stripped
    return mcp_result(ok=True, file=file, **merged)


def mcp_from_list(
    items: list | None,
    *,
    file: str | None = None,
    key: str = "items",
    **payload: object,
) -> dict[str, object]:
    if items is None:
        return mcp_result(ok=False, file=file, error="No response from server", **payload)

    merged = dict(payload)
    merged[key] = items
    return mcp_result(ok=True, file=file, **merged)
