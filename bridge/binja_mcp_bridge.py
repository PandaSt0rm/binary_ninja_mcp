import argparse as _argparse
import functools as _functools
import json as _json
import os as _os
import re as _re
import sys as _sys
import time as _time
import traceback as _tb
import urllib.parse as _urllib_parse
from pathlib import Path as _Path


# Install a very-early excepthook so any ImportError at module import time is captured.
def _bridge_excepthook(exc_type, exc, tb):
    # Print to stderr for interactive runs
    _tb.print_exception(exc_type, exc, tb, file=_sys.stderr)


_sys.excepthook = _bridge_excepthook

import requests
import anyio
from mcp.server.fastmcp import FastMCP

try:
    from binary_ninja_mcp.config import (
        SERVER_NAME,
        build_mcp_server_config,
        resolve_server_url,
    )
except Exception:
    _here = _Path(__file__).resolve().parent
    _root = _here.parent
    if str(_root) not in _sys.path:
        _sys.path.insert(0, str(_root))
    from config import SERVER_NAME, build_mcp_server_config, resolve_server_url

binja_server_url = resolve_server_url()
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


def _set_server_url(url: str):
    global binja_server_url
    binja_server_url = url


def _float_env(name: str, default: float) -> float:
    raw = _os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except Exception:
        return default


def _retry_max_wait() -> float:
    return _float_env("BINARY_NINJA_MCP_RETRY_MAX_WAIT", 20.0)


def _retry_after_default() -> float:
    return _float_env("BINARY_NINJA_MCP_RETRY_AFTER", 5.0)


def _status_timeout() -> float:
    return _float_env("BINARY_NINJA_MCP_STATUS_TIMEOUT", 3.0)


def _long_timeout() -> float:
    return _float_env("BINARY_NINJA_MCP_LONG_TIMEOUT", 120.0)


async def _run_in_thread(func, /, *args, **kwargs):
    return await anyio.to_thread.run_sync(
        _functools.partial(func, *args, **kwargs),
        abandon_on_cancel=True,
    )


def _parse_retry_after(response) -> float:
    header = response.headers.get("Retry-After")
    if header:
        try:
            value = float(header)
            return max(0.0, value)
        except Exception:
            pass
    return _retry_after_default()


def _request_with_retry(
    method: str,
    url: str,
    *,
    data=None,
    timeout: float | None = None,
):
    max_wait = _retry_max_wait()
    deadline = None
    if max_wait > 0:
        deadline = _time.monotonic() + max_wait
    while True:
        if timeout is None:
            response = requests.request(method, url, data=data)
        else:
            response = requests.request(method, url, data=data, timeout=timeout)
        response.encoding = "utf-8"
        if response.status_code != 503:
            return response
        if deadline is None:
            return response
        remaining = deadline - _time.monotonic()
        if remaining <= 0:
            return response
        wait = min(_parse_retry_after(response), remaining)
        if wait > 0:
            _time.sleep(wait)
        else:
            _time.sleep(0.1)


def _active_filename() -> str:
    """Return the currently active filename as known by the server."""
    try:
        st = get_json("status", timeout=_status_timeout())
        if isinstance(st, dict) and st.get("filename"):
            return str(st.get("filename"))
    except Exception:
        pass
    return "(none)"


def _mcp_result(*, ok: bool, file: str | None = None, **payload: object) -> dict:
    """Standard MCP tool response envelope.

    All tools return a JSON-serializable dict with:
    - ok: boolean success flag
    - file: active filename (best-effort)
    - tool-specific payload fields
    """

    out: dict[str, object] = {"ok": ok, **payload}
    out.setdefault("file", file or _active_filename())
    return out


def _mcp_from_json(
    data: object,
    *,
    file: str | None = None,
    request_info: object | None = None,
    **payload: object,
) -> dict:
    # We treat any caller-provided payload as request context, but only include it on errors.
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
        return _mcp_result(ok=False, file=file, **out)

    if isinstance(data, dict):
        if "error" in data:
            ok = False
        elif isinstance(data.get("success"), bool):
            ok = bool(data.get("success"))
        else:
            ok = True

        # Strip reserved envelope keys to prevent accidental clashes.
        out = dict(data)
        out.pop("ok", None)
        out.pop("file", None)

        if not ok and request_context is not None:
            out["request"] = request_context

        return _mcp_result(ok=ok, file=file, **out)

    # Non-dict responses are treated as success; keep output lean.
    return _mcp_result(ok=True, file=file, raw=data)


def _mcp_from_text(
    text: str | None, *, file: str | None = None, key: str = "text", **payload: object
) -> dict:
    if text is None:
        return _mcp_result(ok=False, file=file, error="No response from server", **payload)
    stripped = str(text).strip()
    if stripped.startswith(("Error ", "Request failed")):
        return _mcp_result(ok=False, file=file, error=stripped, **payload)

    merged = dict(payload)
    merged[key] = stripped
    return _mcp_result(ok=True, file=file, **merged)


def _mcp_from_list(
    items: list | None, *, file: str | None = None, key: str = "items", **payload: object
) -> dict:
    if items is None:
        return _mcp_result(ok=False, file=file, error="No response from server", **payload)

    merged = dict(payload)
    merged[key] = items
    return _mcp_result(ok=True, file=file, **merged)


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


def safe_get(endpoint: str, params: dict | None = None, timeout: float | None = 20) -> list:
    """
    Perform a GET request. If 'params' is given, we convert it to a query string.
    """
    if params is None:
        params = {}
    query_string = _urllib_parse.urlencode(params, doseq=True)
    url = f"{binja_server_url}/{endpoint}"
    if query_string:
        url += "?" + query_string

    try:
        response = _request_with_retry("GET", url, timeout=timeout)
        if response.ok:
            return response.text.splitlines()
        return [f"Error {response.status_code}: {response.text.strip()}"]
    except Exception as e:
        return [f"Request failed: {e!s}"]


def get_json(endpoint: str, params: dict | None = None, timeout: float | None = 20):
    """
    Perform a GET and return parsed JSON.
    - On 2xx: returns parsed JSON.
    - On 4xx/5xx: attempts to parse JSON body and return it; if not JSON, returns {'error': 'Error <code>: <text>'}.
    Returns None only on transport errors.
    """
    if params is None:
        params = {}
    query_string = _urllib_parse.urlencode(params, doseq=True)
    url = f"{binja_server_url}/{endpoint}"
    if query_string:
        url += "?" + query_string
    try:
        response = _request_with_retry("GET", url, timeout=timeout)
        # Try to parse JSON regardless of status
        try:
            data = response.json()
        except Exception:
            data = None
        if response.ok:
            return data
        # Non-OK: return parsed error object if available; otherwise synthesize one
        if isinstance(data, dict):
            # Ensure at least an error field for LLMs
            if "error" not in data:
                data = {"error": str(data)}
            data.setdefault("status", response.status_code)
            return data
        text = (response.text or "").strip()
        return {"error": f"Error {response.status_code}: {text}"}
    except Exception as e:
        return {"error": f"Request failed: {e!s}"}


def post_json(endpoint: str, data: dict | str | None = None, timeout: float | None = 20):
    """Perform a POST and return parsed JSON.

    Mirrors get_json() behavior for error handling.
    """
    url = f"{binja_server_url}/{endpoint}"
    try:
        response = _request_with_retry("POST", url, data=data, timeout=timeout)
        try:
            parsed = response.json()
        except Exception:
            parsed = None
        if response.ok:
            return parsed
        if isinstance(parsed, dict):
            if "error" not in parsed:
                parsed = {"error": str(parsed)}
            parsed.setdefault("status", response.status_code)
            return parsed
        text = (response.text or "").strip()
        return {"error": f"Error {response.status_code}: {text}"}
    except Exception as e:
        return {"error": f"Request failed: {e!s}"}


def get_text(endpoint: str, params: dict | None = None, timeout: float | None = 20) -> str:
    """Perform a GET and return raw text (or an error string)."""
    if params is None:
        params = {}
    query_string = _urllib_parse.urlencode(params, doseq=True)
    url = f"{binja_server_url}/{endpoint}"
    if query_string:
        url += "?" + query_string
    try:
        response = _request_with_retry("GET", url, timeout=timeout)
        if response.ok:
            return response.text
        return f"Error {response.status_code}: {response.text.strip()}"
    except Exception as e:
        return f"Request failed: {e!s}"


def safe_post(endpoint: str, data: dict | str) -> str:
    try:
        if isinstance(data, dict):
            response = _request_with_retry(
                "POST", f"{binja_server_url}/{endpoint}", data=data, timeout=20
            )
        else:
            response = _request_with_retry(
                "POST",
                f"{binja_server_url}/{endpoint}",
                data=data.encode("utf-8"),
                timeout=20,
            )
        if response.ok:
            return response.text.strip()
        return f"Error {response.status_code}: {response.text.strip()}"
    except Exception as e:
        return f"Request failed: {e!s}"


@tool()
def list_methods(offset: int = 0, limit: int = 100) -> dict:
    """List all function names in the program with pagination."""

    file = _active_filename()
    params = {"offset": offset, "limit": limit}
    data = get_json("methods", params)
    if isinstance(data, dict) and "error" not in data:
        return _mcp_result(
            ok=True,
            file=file,
            offset=offset,
            limit=limit,
            functions=data.get("functions", []) or [],
        )
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_entry_points() -> dict:
    """List entry point(s) of the loaded binary."""

    file = _active_filename()
    data = get_json("entryPoints")
    return _mcp_from_json(data, file=file)


@tool()
def retype_variable(function_name: str, variable_name: str, type_str: str) -> dict:
    """Retype a variable in a function."""

    file = _active_filename()
    params = {
        "functionName": function_name,
        "variableName": variable_name,
        "type": type_str,
    }
    data = get_json("retypeVariable", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def rename_single_variable(function_name: str, variable_name: str, new_name: str) -> dict:
    """Rename a variable in a function."""

    file = _active_filename()
    params = {
        "functionName": function_name,
        "variableName": variable_name,
        "newName": new_name,
    }
    data = get_json("renameVariable", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def rename_multi_variables(
    function_identifier: str,
    mapping_json: str = "",
    pairs: str = "",
    renames_json: str = "",
) -> dict:
    """Rename multiple local variables in one call.

    - function_identifier: function name or address (hex)
    - Provide either mapping_json (JSON object old->new), renames_json (JSON array of {old,new}), or pairs ("old1:new1,old2:new2").

    Returns per-item results and totals.
    """

    file = _active_filename()
    params: dict[str, object] = {}
    ident = (function_identifier or "").strip()
    if _is_int_like(ident):
        params["address"] = ident
    else:
        params["functionName"] = ident

    if renames_json:
        try:
            _json.loads(renames_json)
        except Exception:
            return _mcp_result(ok=False, file=file, error="renames_json is not valid JSON")
        params["renames"] = renames_json
    elif mapping_json:
        try:
            _json.loads(mapping_json)
        except Exception:
            return _mcp_result(ok=False, file=file, error="mapping_json is not valid JSON")
        params["mapping"] = mapping_json
    elif pairs:
        params["pairs"] = pairs
    else:
        return _mcp_result(
            ok=False, file=file, error="Provide mapping_json, renames_json, or pairs"
        )

    data = post_json("renameVariables", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def define_types(c_code: str) -> dict:
    """Define types from a C code string."""

    file = _active_filename()
    data = post_json("defineTypes", {"cCode": c_code})
    return _mcp_from_json(data, file=file)


@tool()
def list_classes(offset: int = 0, limit: int = 100) -> dict:
    """List all namespace/class names in the program with pagination."""

    file = _active_filename()
    params = {"offset": offset, "limit": limit}
    data = get_json("classes", params)
    if isinstance(data, dict) and "error" not in data:
        return _mcp_result(
            ok=True,
            file=file,
            offset=offset,
            limit=limit,
            classes=data.get("classes", []) or [],
        )
    return _mcp_from_json(data, file=file, **params)


@tool()
def hexdump_address(address: str, length: int = -1) -> dict:
    """Hexdump data starting at an address.

    When `length < 0`, the server attempts to read the exact defined size.
    """

    file = _active_filename()
    params = {"address": address, "length": length}
    text = get_text("hexdump", params, timeout=_long_timeout())
    return _mcp_from_text(text, file=file, key="hexdump", **params)


@tool()
def hexdump_data(name_or_address: str, length: int = -1) -> dict:
    """Hexdump a data symbol by name or address."""

    ident = (name_or_address or "").strip()
    if ident.startswith("0x"):
        return hexdump_address(ident, length)

    file = _active_filename()
    params = {"name": ident, "length": length}
    text = get_text("hexdumpByName", params, timeout=_long_timeout())
    return _mcp_from_text(text, file=file, key="hexdump", **params)


@tool()
def get_data_decl(name_or_address: str, length: int = -1) -> dict:
    """Return a declaration and a hexdump for a data symbol."""

    file = _active_filename()
    ident = (name_or_address or "").strip()
    params: dict[str, object] = (
        {"name": ident} if not ident.startswith("0x") else {"address": ident}
    )
    params["length"] = length
    data = get_json("getDataDecl", params, timeout=_long_timeout())
    return _mcp_from_json(data, file=file, **params)


@tool()
def decompile_function(name: str) -> dict:
    """Decompile a specific function by name."""

    file = _active_filename()
    data = get_json("decompile", {"name": name}, timeout=_long_timeout())
    return _mcp_from_json(data, file=file, name=name)


@tool()
def get_il(name_or_address: str, view: str = "hlil", ssa: bool = False) -> dict:
    """Get IL for a function in the selected view."""

    file = _active_filename()
    ident = (name_or_address or "").strip()
    params: dict[str, object] = {"view": view, "ssa": int(bool(ssa))}
    if _is_int_like(ident):
        params["address"] = ident
    else:
        params["name"] = ident
    data = get_json("il", params, timeout=_long_timeout())
    return _mcp_from_json(data, file=file, requested=name_or_address, view=view, ssa=ssa)


@tool()
def fetch_disassembly(name: str) -> dict:
    """Retrieve disassembly for a function by name."""

    file = _active_filename()
    data = get_json("assembly", {"name": name}, timeout=_long_timeout())
    return _mcp_from_json(data, file=file, name=name)


@tool()
def rename_function(old_name: str, new_name: str) -> dict:
    """Rename a function by its current name (or address) to a new user-defined name."""

    file = _active_filename()
    params = {"oldName": old_name, "newName": new_name}
    data = post_json("renameFunction", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def rename_data(address: str, new_name: str) -> dict:
    """Rename a data label at the specified address."""

    file = _active_filename()
    params = {"address": address, "newName": new_name}
    data = post_json("renameData", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def set_comment(address: str, comment: str) -> dict:
    """Set a comment at a specific address."""

    file = _active_filename()
    params = {"address": address, "comment": comment}
    data = post_json("comment", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def set_function_comment(function_name: str, comment: str) -> dict:
    """Set a comment for a function."""

    file = _active_filename()
    params = {"name": function_name, "comment": comment}
    data = post_json("comment/function", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_comment(address: str) -> dict:
    """Get the comment at a specific address."""

    file = _active_filename()
    params = {"address": address}
    data = get_json("comment", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_function_comment(function_name: str) -> dict:
    """Get the comment for a function."""

    file = _active_filename()
    params = {"name": function_name}
    data = get_json("comment/function", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def list_segments(offset: int = 0, limit: int = 100) -> dict:
    """List all memory segments in the program with pagination."""

    file = _active_filename()
    params = {"offset": offset, "limit": limit}
    data = get_json("segments", params)
    if isinstance(data, dict) and "error" not in data:
        return _mcp_result(
            ok=True,
            file=file,
            offset=offset,
            limit=limit,
            segments=data.get("segments", []) or [],
        )
    return _mcp_from_json(data, file=file, **params)


@tool()
def list_sections(offset: int = 0, limit: int = 100) -> dict:
    """List sections in the program with pagination."""

    file = _active_filename()
    params = {"offset": offset, "limit": limit}
    data = get_json("sections", params)
    if isinstance(data, dict) and "error" not in data:
        return _mcp_result(
            ok=True,
            file=file,
            offset=offset,
            limit=limit,
            sections=data.get("sections", []) or [],
        )
    return _mcp_from_json(data, file=file, **params)


@tool()
def list_imports(offset: int = 0, limit: int = 100) -> dict:
    """List imported symbols in the program with pagination."""

    file = _active_filename()
    params = {"offset": offset, "limit": limit}
    data = get_json("imports", params)
    if isinstance(data, dict) and "error" not in data:
        return _mcp_result(
            ok=True,
            file=file,
            offset=offset,
            limit=limit,
            imports=data.get("imports", []) or [],
        )
    return _mcp_from_json(data, file=file, **params)


@tool()
def list_strings(offset: int = 0, count: int = 100) -> dict:
    """List strings in the database (paginated)."""

    file = _active_filename()
    params = {"offset": offset, "limit": count}
    data = get_json("strings", params, timeout=_long_timeout())
    if isinstance(data, dict) and "error" not in data:
        return _mcp_result(
            ok=True,
            file=file,
            offset=offset,
            limit=count,
            strings=data.get("strings", []) or [],
        )
    return _mcp_from_json(data, file=file, **params)


@tool()
def list_strings_filter(offset: int = 0, count: int = 100, filter: str = "") -> dict:
    """List matching strings in the database (paginated, filtered)."""

    file = _active_filename()
    params = {"offset": offset, "limit": count, "filter": filter}
    data = get_json("strings/filter", params, timeout=_long_timeout())
    if isinstance(data, dict) and "error" not in data:
        return _mcp_result(
            ok=True,
            file=file,
            offset=offset,
            limit=count,
            filter=filter,
            strings=data.get("strings", []) or [],
            total=data.get("total"),
        )
    return _mcp_from_json(data, file=file, **params)


@tool()
def list_local_types(offset: int = 0, count: int = 200, include_libraries: bool = False) -> dict:
    """List local types in the database (paginated)."""

    file = _active_filename()
    params = {
        "offset": offset,
        "limit": count,
        "includeLibraries": int(bool(include_libraries)),
    }
    data = get_json("localTypes", params, timeout=_long_timeout())
    if isinstance(data, dict) and "error" not in data:
        return _mcp_result(
            ok=True,
            file=file,
            offset=offset,
            limit=count,
            includeLibraries=bool(include_libraries),
            types=data.get("types", []) or [],
        )
    return _mcp_from_json(data, file=file, **params)


@tool()
def search_types(
    query: str, offset: int = 0, count: int = 200, include_libraries: bool = False
) -> dict:
    """Search local types whose name or declaration contains the substring."""

    file = _active_filename()
    params = {
        "query": query,
        "offset": offset,
        "limit": count,
        "includeLibraries": int(bool(include_libraries)),
    }
    data = get_json("searchTypes", params, timeout=_long_timeout())
    if isinstance(data, dict) and "error" not in data:
        return _mcp_result(
            ok=True,
            file=file,
            query=query,
            offset=offset,
            limit=count,
            includeLibraries=bool(include_libraries),
            types=data.get("types", []) or [],
            total=data.get("total"),
        )
    return _mcp_from_json(data, file=file, **params)


@tool()
def list_all_strings() -> dict:
    """List all strings in the database (no pagination)."""

    file = _active_filename()
    data = get_json("allStrings", timeout=_long_timeout())
    if isinstance(data, dict) and "error" not in data:
        return _mcp_result(ok=True, file=file, strings=data.get("strings", []) or [])
    return _mcp_from_json(data, file=file)


@tool()
def list_exports(offset: int = 0, limit: int = 100) -> dict:
    """List exported functions/symbols with pagination."""

    file = _active_filename()
    params = {"offset": offset, "limit": limit}
    data = get_json("exports", params)
    if isinstance(data, dict) and "error" not in data:
        return _mcp_result(
            ok=True,
            file=file,
            offset=offset,
            limit=limit,
            exports=data.get("exports", []) or [],
        )
    return _mcp_from_json(data, file=file, **params)


@tool()
def list_namespaces(offset: int = 0, limit: int = 100) -> dict:
    """List all non-global namespaces in the program with pagination."""

    file = _active_filename()
    params = {"offset": offset, "limit": limit}
    data = get_json("namespaces", params)
    if isinstance(data, dict) and "error" not in data:
        return _mcp_result(
            ok=True,
            file=file,
            offset=offset,
            limit=limit,
            namespaces=data.get("namespaces", []) or [],
        )
    return _mcp_from_json(data, file=file, **params)


@tool()
def list_data_items(offset: int = 0, limit: int = 100) -> dict:
    """List defined data labels and their values with pagination."""

    file = _active_filename()
    params = {"offset": offset, "limit": limit}
    data = get_json("data", params)
    if isinstance(data, dict) and "error" not in data:
        return _mcp_result(
            ok=True, file=file, offset=offset, limit=limit, data=data.get("data", []) or []
        )
    return _mcp_from_json(data, file=file, **params)


@tool()
def search_functions_by_name(query: str, offset: int = 0, limit: int = 100) -> dict:
    """Search for functions whose name contains the given substring."""

    file = _active_filename()
    if not query:
        return _mcp_result(ok=False, file=file, error="Query string is required", query=query)

    params = {"query": query, "offset": offset, "limit": limit}
    data = get_json("searchFunctions", params)
    if isinstance(data, dict) and "error" not in data:
        return _mcp_result(
            ok=True,
            file=file,
            query=query,
            offset=offset,
            limit=limit,
            matches=data.get("matches", []) or [],
        )
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_binary_status() -> dict:
    """Get the current status of the loaded binary."""

    data = get_json("status", timeout=_status_timeout())
    return _mcp_from_json(data, file="(none)")


@tool()
def list_binaries() -> dict:
    """List managed/open binaries known to the server with ids and active flag."""

    data = get_json("binaries", timeout=_status_timeout())
    return _mcp_from_json(data, file="(none)")


@tool()
def select_binary(view: str) -> dict:
    """Select which binary to analyze by id, filename, or basename."""

    data = get_json("selectBinary", {"view": view}, timeout=_long_timeout())
    return _mcp_from_json(data, file="(none)", view=view)


@tool()
def delete_comment(address: str) -> dict:
    """Delete the comment at a specific address."""

    file = _active_filename()
    params = {"address": address, "_method": "DELETE"}
    data = post_json("comment", params)
    return _mcp_from_json(data, file=file, address=address)


@tool()
def delete_function_comment(function_name: str) -> dict:
    """Delete the comment for a function."""

    file = _active_filename()
    params = {"name": function_name, "_method": "DELETE"}
    data = post_json("comment/function", params)
    return _mcp_from_json(data, file=file, name=function_name)


@tool()
def function_at(address: str) -> dict:
    """Retrieve the name(s) of the function(s) containing an address."""

    file = _active_filename()
    params = {"address": address}
    data = get_json("functionAt", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_user_defined_type(type_name: str) -> dict:
    """Retrieve a user-defined type definition (struct/enum/typedef/union)."""

    file = _active_filename()
    params = {"name": type_name}
    data = get_json("getUserDefinedType", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_xrefs_to(address: str) -> dict:
    """Get all cross references (code and data) to an address."""

    file = _active_filename()
    params = {"address": address}
    data = get_json("getXrefsTo", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_xrefs_to_field(struct_name: str, field_name: str) -> dict:
    """Get cross references to a named struct field (member)."""

    file = _active_filename()
    params = {"struct": struct_name, "field": field_name}
    data = get_json("getXrefsToField", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_xrefs_to_struct(struct_name: str) -> dict:
    """Get cross references/usages related to a struct name."""

    file = _active_filename()
    params = {"name": struct_name}
    data = get_json("getXrefsToStruct", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_xrefs_to_type(type_name: str) -> dict:
    """Get xrefs/usages related to a struct or type name."""

    file = _active_filename()
    params = {"name": type_name}
    data = get_json("getXrefsToType", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_xrefs_to_enum(enum_name: str) -> dict:
    """Get usages/xrefs of an enum by scanning for member values and matches."""

    file = _active_filename()
    params = {"name": enum_name}
    data = get_json("getXrefsToEnum", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_xrefs_to_union(union_name: str) -> dict:
    """Get cross references/usages related to a union type by name."""

    file = _active_filename()
    params = {"name": union_name}
    data = get_json("getXrefsToUnion", params)
    return _mcp_from_json(data, file=file, **params)


@tool()
def get_stack_frame_vars(function_identifier: str) -> dict:
    """Get stack frame variable information for a function by name or address."""

    file = _active_filename()
    ident = (function_identifier or "").strip()
    params: dict[str, object] = {}
    if _is_int_like(ident):
        params["address"] = ident
    else:
        params["name"] = ident

    data = get_json("getStackFrameVars", params, timeout=_long_timeout())
    return _mcp_from_json(data, file=file, identifier=function_identifier)


@tool()
def format_value(address: str, text: str, size: int = 0) -> dict:
    """Convert and annotate a value at an address in Binary Ninja."""

    file = _active_filename()
    params = {"address": address, "text": text, "size": size}
    data = get_json("formatValue", params, timeout=_long_timeout())
    return _mcp_from_json(data, file=file, **params)


@tool()
def convert_number(text: str, size: int = 0) -> dict:
    """Convert a number/string to multiple representations (hex/dec/bin, LE/BE, C literals)."""

    params = {"text": text, "size": size}
    data = get_json("convertNumber", params, timeout=_long_timeout())
    return _mcp_from_json(data, file="(none)", **params)


@tool()
def get_type_info(type_name: str) -> dict:
    """Resolve a type name and return its declaration and details."""

    file = _active_filename()
    params = {"name": type_name}
    data = get_json("getTypeInfo", params, timeout=_long_timeout())
    return _mcp_from_json(data, file=file, **params)


@tool()
def set_function_prototype(name_or_address: str, prototype: str) -> dict:
    """Set a function's prototype by name or address."""

    file = _active_filename()
    ident = (name_or_address or "").strip()
    params: dict[str, object] = {"prototype": prototype}
    if _is_int_like(ident):
        params["address"] = ident
    else:
        params["name"] = ident

    data = post_json("setFunctionPrototype", params, timeout=_long_timeout())
    return _mcp_from_json(data, file=file, requested=name_or_address)


@tool()
def make_function_at(address: str, platform: str = "") -> dict:
    """Create a function at the given address."""

    file = _active_filename()
    params: dict[str, object] = {"address": address}
    if platform:
        params["platform"] = platform
    data = get_json("makeFunctionAt", params, timeout=_long_timeout())
    return _mcp_from_json(data, file=file, **params)


@tool()
def list_platforms() -> dict:
    """List all available platform names from Binary Ninja."""

    data = get_json("platforms", timeout=_status_timeout())
    return _mcp_from_json(data, file="(none)")


@tool()
def declare_c_type(c_declaration: str) -> dict:
    """Create or update a local type from a C declaration."""

    file = _active_filename()
    data = post_json("declareCType", {"declaration": c_declaration}, timeout=_long_timeout())
    return _mcp_from_json(data, file=file)


@tool()
def set_local_variable_type(function_address: str, variable_name: str, new_type: str) -> dict:
    """Set a local variable's type."""

    file = _active_filename()
    params = {
        "functionAddress": function_address,
        "variableName": variable_name,
        "newType": new_type,
    }
    data = get_json("setLocalVariableType", params, timeout=_long_timeout())
    return _mcp_from_json(data, file=file, **params)


@tool()
def patch_bytes(address: str, data: str, save_to_file: bool = True) -> dict:
    """Patch bytes at a given address in the binary."""

    file = _active_filename()
    if isinstance(save_to_file, str):
        save_to_file = save_to_file.lower() not in ("false", "0", "no")

    params = {"address": address, "data": data, "save_to_file": save_to_file}
    result = post_json("patch", params, timeout=_long_timeout())
    return _mcp_from_json(result, file=file, request_info=params)


def _config_json(prefer_uv: bool, dev: bool, server_url: str) -> str:
    cfg = build_mcp_server_config(
        prefer_uv=prefer_uv,
        dev=dev,
        repo_root=str(_Path(__file__).resolve().parent.parent),
        server_url=server_url,
        fallback_command=_sys.executable,
        fallback_args=[_Path(__file__).resolve()],
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


if __name__ == "__main__":
    main()
