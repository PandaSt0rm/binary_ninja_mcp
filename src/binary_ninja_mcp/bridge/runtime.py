from __future__ import annotations

import functools as _functools

import anyio
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("binja-mcp")


def tool(**tool_kwargs):
    """Register a sync function as an MCP tool without blocking the event loop."""

    def decorator(fn):
        cfg = dict(tool_kwargs)
        cfg.setdefault("name", fn.__name__)
        cfg.setdefault("description", fn.__doc__ or "")

        @mcp.tool(**cfg)
        @_functools.wraps(fn)
        async def _wrapper(*args, **kwargs):  # pragma: no cover - exercised via MCP runtime
            return await _run_in_thread(fn, *args, **kwargs)

        return fn

    return decorator


async def _run_in_thread(func, /, *args, **kwargs):
    return await anyio.to_thread.run_sync(
        _functools.partial(func, *args, **kwargs),
        abandon_on_cancel=True,
    )
