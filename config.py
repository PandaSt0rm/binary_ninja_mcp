from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 9009
SERVER_NAME = "binary_ninja_mcp"
GITHUB_REPO = "https://github.com/fosdickio/binary_ninja_mcp"


def resolve_server_url(url: str | None = None, host: str | None = None, port: str | int | None = None) -> str:
    """Resolve the Binary Ninja MCP HTTP server URL with env/arg fallbacks."""
    if url:
        return url

    env_url = os.environ.get("BINARY_NINJA_MCP_URL")
    if env_url:
        return env_url

    host_val = host or os.environ.get("BINARY_NINJA_MCP_HOST") or DEFAULT_HOST
    port_val = port or os.environ.get("BINARY_NINJA_MCP_PORT") or DEFAULT_PORT
    try:
        port_int = int(port_val)
        port_val = port_int
    except Exception:
        pass
    return f"http://{host_val}:{port_val}"


def _auto_repo_root(start: Path | None = None) -> str | None:
    """Walk upward to find a pyproject.toml and return its directory."""
    p = start or Path(__file__).resolve()
    for parent in [p] + list(p.parents):
        candidate = parent / "pyproject.toml"
        if candidate.exists():
            return str(parent)
    return None


def uv_available() -> bool:
    return shutil.which("uvx") is not None or shutil.which("uv") is not None


def uv_command(*, dev: bool = False, repo_root: str | None = None) -> tuple[str, list[str]]:
    if dev:
        root = repo_root or _auto_repo_root()
        if root:
            return "uv", ["--directory", root, "run", "binary-ninja-mcp"]
    cmd = "uvx" if shutil.which("uvx") else "uv"
    return cmd, ["--from", f"git+{GITHUB_REPO}", "binary-ninja-mcp"]


def build_mcp_server_config(
    *,
    prefer_uv: bool = True,
    dev: bool = False,
    repo_root: str | None = None,
    env: dict | None = None,
    server_url: str | None = None,
    fallback_command: str | None = None,
    fallback_args: list[str] | str | Path | None = None,
    timeout: int = 1800,
) -> dict:
    """Create an MCP server config entry that prefers uv/uvx when available."""

    env_out = dict(env or {})
    if server_url:
        env_out.setdefault("BINARY_NINJA_MCP_URL", server_url)

    command: str | None = None
    args: list[str] | None = None

    if prefer_uv and uv_available():
        command, args = uv_command(dev=dev, repo_root=repo_root)

    if command is None:
        command = fallback_command or sys.executable
        if fallback_args is None:
            fallback_args = [
                str(Path(__file__).resolve().parent / "bridge" / "binja_mcp_bridge.py")
            ]
        if isinstance(fallback_args, (str, Path)):
            args = [str(fallback_args)]
        else:
            args = list(fallback_args)

    config = {"command": command, "args": args, "timeout": timeout, "disabled": False}
    if env_out:
        config["env"] = env_out
    return config
