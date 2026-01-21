from __future__ import annotations

import os
import time
import urllib.parse
from typing import Any

import requests

from ..config import resolve_server_url

_SERVER_URL = resolve_server_url()


def set_server_url(url: str) -> None:
    global _SERVER_URL
    _SERVER_URL = url


def get_server_url() -> str:
    return _SERVER_URL


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except Exception:
        return default


def retry_max_wait() -> float:
    return _float_env("BINARY_NINJA_MCP_RETRY_MAX_WAIT", 20.0)


def retry_after_default() -> float:
    return _float_env("BINARY_NINJA_MCP_RETRY_AFTER", 5.0)


def status_timeout() -> float:
    return _float_env("BINARY_NINJA_MCP_STATUS_TIMEOUT", 3.0)


def long_timeout() -> float:
    return _float_env("BINARY_NINJA_MCP_LONG_TIMEOUT", 120.0)


def _parse_retry_after(response) -> float:
    header = response.headers.get("Retry-After")
    if header:
        try:
            value = float(header)
            return max(0.0, value)
        except Exception:
            pass
    return retry_after_default()


def _request_with_retry(
    method: str,
    url: str,
    *,
    data: Any | None = None,
    timeout: float | None = None,
):
    max_wait = retry_max_wait()
    deadline = None
    if max_wait > 0:
        deadline = time.monotonic() + max_wait
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
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return response
        wait = min(_parse_retry_after(response), remaining)
        if wait > 0:
            time.sleep(wait)
        else:
            time.sleep(0.1)


def _build_url(endpoint: str, params: dict | None = None) -> str:
    query_string = ""
    if params:
        query_string = urllib.parse.urlencode(params, doseq=True)
    url = f"{get_server_url()}/{endpoint}"
    if query_string:
        url += "?" + query_string
    return url


def _request(
    method: str,
    endpoint: str,
    *,
    params: dict | None = None,
    data: Any | None = None,
    timeout: float | None = None,
):
    url = _build_url(endpoint, params)
    return _request_with_retry(method, url, data=data, timeout=timeout)


def _parse_json_response(response: requests.Response) -> dict[str, Any] | None:
    try:
        return response.json()
    except Exception:
        return None


def safe_get(endpoint: str, params: dict | None = None, timeout: float | None = 20) -> list[str]:
    """Perform a GET request and return lines (or an error line)."""
    try:
        response = _request("GET", endpoint, params=params, timeout=timeout)
        if response.ok:
            return response.text.splitlines()
        return [f"Error {response.status_code}: {response.text.strip()}"]
    except Exception as exc:
        return [f"Request failed: {exc!s}"]


def get_json(endpoint: str, params: dict | None = None, timeout: float | None = 20):
    """
    Perform a GET and return parsed JSON.
    - On 2xx: returns parsed JSON.
    - On 4xx/5xx: attempts to parse JSON body and return it; if not JSON, returns {'error': 'Error <code>: <text>'}.
    Returns None only when a 2xx response has an empty body.
    """
    try:
        response = _request("GET", endpoint, params=params, timeout=timeout)
        data = _parse_json_response(response)
        if response.ok:
            return data
        if isinstance(data, dict):
            if "error" not in data:
                data = {"error": str(data)}
            payload: dict[str, Any] = dict(data)
            payload.setdefault("status", response.status_code)
            return payload
        text = (response.text or "").strip()
        return {"error": f"Error {response.status_code}: {text}"}
    except Exception as exc:
        return {"error": f"Request failed: {exc!s}"}


def post_json(endpoint: str, data: dict | str | None = None, timeout: float | None = 20):
    """Perform a POST and return parsed JSON (mirrors get_json error handling)."""
    try:
        response = _request("POST", endpoint, data=data, timeout=timeout)
        parsed = _parse_json_response(response)
        if response.ok:
            return parsed
        if isinstance(parsed, dict):
            if "error" not in parsed:
                parsed = {"error": str(parsed)}
            payload: dict[str, Any] = dict(parsed)
            payload.setdefault("status", response.status_code)
            return payload
        text = (response.text or "").strip()
        return {"error": f"Error {response.status_code}: {text}"}
    except Exception as exc:
        return {"error": f"Request failed: {exc!s}"}


def get_text(endpoint: str, params: dict | None = None, timeout: float | None = 20) -> str:
    """Perform a GET and return raw text (or an error string)."""
    try:
        response = _request("GET", endpoint, params=params, timeout=timeout)
        if response.ok:
            return response.text
        return f"Error {response.status_code}: {response.text.strip()}"
    except Exception as exc:
        return f"Request failed: {exc!s}"


def safe_post(endpoint: str, data: dict | str) -> str:
    try:
        payload = data.encode("utf-8") if isinstance(data, str) else data
        response = _request("POST", endpoint, data=payload, timeout=20)
        if response.ok:
            return response.text.strip()
        return f"Error {response.status_code}: {response.text.strip()}"
    except Exception as exc:
        return f"Request failed: {exc!s}"
