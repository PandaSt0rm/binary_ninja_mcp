import argparse as _argparse
import json as _json
import sys as _sys
import traceback as _tb


# Install a very-early excepthook so any ImportError at module import time is captured.
def _bridge_excepthook(exc_type, exc, tb):
    # Print to stderr for interactive runs
    _tb.print_exception(exc_type, exc, tb, file=_sys.stderr)


_sys.excepthook = _bridge_excepthook

from ..config import SERVER_NAME, build_mcp_server_config, resolve_server_url
from . import tool_helpers as _tool_helpers
from . import tools as _tools
from .http_client import (
    get_json,
    get_text,
    post_json,
    safe_get,
    safe_post,
)
from .http_client import (
    get_server_url as _get_http_server_url,
)
from .http_client import (
    long_timeout as _long_timeout,
)
from .http_client import (
    set_server_url as _set_http_server_url,
)
from .http_client import (
    status_timeout as _status_timeout,
)
from .runtime import mcp, tool

binja_server_url = _get_http_server_url()


def _set_server_url(url: str):
    _set_http_server_url(url)
    global binja_server_url
    binja_server_url = url


_HELPER_EXPORTS = tuple(_tool_helpers.__all__)
for _name in _HELPER_EXPORTS:
    globals()[_name] = getattr(_tool_helpers, _name)

_TOOL_EXPORTS = tuple(_tools.__all__)
for _name in _TOOL_EXPORTS:
    globals()[_name] = getattr(_tools, _name)


def _config_json(prefer_uv: bool, dev: bool, server_url: str) -> str:
    cfg = build_mcp_server_config(
        prefer_uv=prefer_uv,
        dev=dev,
        server_url=server_url,
        fallback_command=_sys.executable,
    )
    return _json.dumps({"mcpServers": {SERVER_NAME: cfg}}, indent=2)


def main(argv: list[str] | None = None):
    parser = _argparse.ArgumentParser(description="Binary Ninja MCP bridge (MCP stdio server)")
    parser.add_argument(
        "--server", help="Binary Ninja MCP HTTP server URL (default: env or http://127.0.0.1:9009)"
    )
    parser.add_argument("--host", help="Binary Ninja MCP HTTP server host")
    parser.add_argument("--port", type=int, help="Binary Ninja MCP HTTP server port")
    parser.add_argument(
        "--config", action="store_true", help="Print MCP client config JSON and exit"
    )
    parser.add_argument(
        "--dev", action="store_true", help="Emit config that uses 'uv run' from the repo root"
    )
    parser.add_argument(
        "--no-uv", action="store_true", help="Disable uv/uvx preference when generating config"
    )
    args = parser.parse_args(argv)

    server_url = resolve_server_url(args.server, args.host, args.port)
    _set_server_url(server_url)

    if args.config:
        print(_config_json(not args.no_uv, args.dev, server_url))
        return

    # Important: write any logs to stderr to avoid corrupting MCP stdio JSON-RPC
    print(f"Starting MCP bridge service (Binary Ninja at {server_url})...", file=_sys.stderr)
    try:
        mcp.run()
    except (KeyboardInterrupt, EOFError):
        pass
    except Exception as _e:
        _bridge_excepthook(type(_e), _e, _e.__traceback__)
        raise


__all__ = [
    "mcp",
    "tool",
    "binja_server_url",
    "get_json",
    "get_text",
    "post_json",
    "safe_get",
    "safe_post",
    "_long_timeout",
    "_status_timeout",
    "_set_server_url",
    "_config_json",
    "main",
    *_HELPER_EXPORTS,
    *_TOOL_EXPORTS,
]


if __name__ == "__main__":
    main()
