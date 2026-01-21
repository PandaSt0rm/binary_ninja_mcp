import json
import os
import sys

from binary_ninja_mcp.config import SERVER_NAME, build_mcp_server_config, resolve_server_url

from .python_detection import copy_python_env, create_venv_with_system_python, get_python_executable


def _package_root() -> str:
    # plugin/utils/auto_setup.py -> plugin/utils -> plugin -> binary_ninja_mcp
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _repo_root() -> str:
    # plugin/utils/auto_setup.py -> plugin/utils -> plugin -> binary_ninja_mcp -> src -> repo_root
    return os.path.abspath(os.path.join(_package_root(), "..", ".."))


def _bridge_module_args() -> list[str]:
    return ["-m", "binary_ninja_mcp.bridge.binja_mcp_bridge"]


def _sentinel_path() -> str:
    return os.path.join(_repo_root(), ".mcp_auto_setup_done")


def _venv_dir() -> str:
    return os.path.join(_repo_root(), ".venv")


def _venv_python() -> str:
    d = _venv_dir()
    if sys.platform == "win32":
        # Always prefer a real Python interpreter (python.exe) for MCP stdio servers.
        # Returning binaryninja.exe here causes the MCP client to fail on Windows.
        py = os.path.join(d, "Scripts", "python.exe")
        return py
    return os.path.join(d, "bin", "python3")


def _prefer_uv() -> bool:
    return os.environ.get("BINARY_NINJA_MCP_NO_UV", "").lower() not in ("1", "true", "yes")


def _dev_mode() -> bool:
    return os.environ.get("BINARY_NINJA_MCP_DEV", "").lower() in ("1", "true", "yes")


def _ensure_local_venv() -> str:
    """Create a local venv under the plugin root if missing.

    Returns path to the venv's python executable; falls back to get_python_executable
    on failure.
    """
    vdir = _venv_dir()
    req = os.path.join(_package_root(), "bridge", "requirements.txt")

    try:
        py = create_venv_with_system_python(vdir, req if os.path.exists(req) else None)
        return py if os.path.exists(py) else get_python_executable()
    except Exception:
        return get_python_executable()


def _targets() -> dict:
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        appdata = os.getenv("APPDATA") or os.path.join(home, "AppData", "Roaming")
        return {
            "Cline": (
                os.path.join(
                    appdata, "Code", "User", "globalStorage", "saoudrizwan.claude-dev", "settings"
                ),
                "cline_mcp_settings.json",
            ),
            "Roo Code": (
                os.path.join(
                    appdata,
                    "Code",
                    "User",
                    "globalStorage",
                    "rooveterinaryinc.roo-cline",
                    "settings",
                ),
                "mcp_settings.json",
            ),
            "Claude": (os.path.join(appdata, "Claude"), "claude_desktop_config.json"),
            "Cursor": (os.path.join(home, ".cursor"), "mcp.json"),
            "Windsurf": (os.path.join(home, ".codeium", "windsurf"), "mcp_config.json"),
            "Claude Code": (home, ".claude.json"),
            "LM Studio": (os.path.join(home, ".lmstudio"), "mcp.json"),
        }
    elif sys.platform == "darwin":
        return {
            "Cline": (
                os.path.join(
                    home,
                    "Library",
                    "Application Support",
                    "Code",
                    "User",
                    "globalStorage",
                    "saoudrizwan.claude-dev",
                    "settings",
                ),
                "cline_mcp_settings.json",
            ),
            "Roo Code": (
                os.path.join(
                    home,
                    "Library",
                    "Application Support",
                    "Code",
                    "User",
                    "globalStorage",
                    "rooveterinaryinc.roo-cline",
                    "settings",
                ),
                "mcp_settings.json",
            ),
            "Claude": (
                os.path.join(home, "Library", "Application Support", "Claude"),
                "claude_desktop_config.json",
            ),
            "Cursor": (os.path.join(home, ".cursor"), "mcp.json"),
            "Windsurf": (os.path.join(home, ".codeium", "windsurf"), "mcp_config.json"),
            "Claude Code": (home, ".claude.json"),
            "LM Studio": (os.path.join(home, ".lmstudio"), "mcp.json"),
        }
    elif sys.platform == "linux":
        return {
            "Cline": (
                os.path.join(
                    home,
                    ".config",
                    "Code",
                    "User",
                    "globalStorage",
                    "saoudrizwan.claude-dev",
                    "settings",
                ),
                "cline_mcp_settings.json",
            ),
            "Roo Code": (
                os.path.join(
                    home,
                    ".config",
                    "Code",
                    "User",
                    "globalStorage",
                    "rooveterinaryinc.roo-cline",
                    "settings",
                ),
                "mcp_settings.json",
            ),
            # Claude not supported on Linux
            "Cursor": (os.path.join(home, ".cursor"), "mcp.json"),
            "Windsurf": (os.path.join(home, ".codeium", "windsurf"), "mcp_config.json"),
            "Claude Code": (home, ".claude.json"),
            "LM Studio": (os.path.join(home, ".lmstudio"), "mcp.json"),
        }
    else:
        return {}


def install_mcp_clients(quiet: bool = True) -> int:
    """Install MCP server entries for supported clients.

    Returns the number of configs modified. Creates a sentinel to avoid
    re-running on every Binary Ninja start.
    """
    sentinel = _sentinel_path()
    server_key = SERVER_NAME
    if os.path.exists(sentinel):
        # If sentinel exists but no client has our key yet, proceed anyway
        try:
            targets = _targets()
            for _name, (config_dir, config_file) in targets.items():
                config_path = os.path.join(config_dir, config_file)
                if not os.path.exists(config_path):
                    continue
                with open(config_path, encoding="utf-8") as f:
                    data = f.read().strip()
                    if not data:
                        continue
                    cfg = json.loads(data)
                if isinstance(cfg, dict) and server_key in cfg.get("mcpServers", {}):
                    return 0
            # No installs found; ignore the sentinel and continue
        except Exception:
            # On any error, fall through and attempt install
            pass

    targets = _targets()
    if not targets:
        return 0

    env: dict[str, str] = {}
    copy_python_env(env)
    bridge_args = _bridge_module_args()
    command = _ensure_local_venv()
    server_url = resolve_server_url()
    prefer_uv = _prefer_uv()
    dev_mode = _dev_mode()

    modified = 0
    for _name, (config_dir, config_file) in targets.items():
        if not os.path.exists(config_dir):
            continue
        config_path = os.path.join(config_dir, config_file)
        if not os.path.exists(config_path):
            config = {}
        else:
            try:
                with open(config_path, encoding="utf-8") as f:
                    data = f.read().strip()
                    config = json.loads(data) if data else {}
            except Exception:
                continue

        config.setdefault("mcpServers", {})
        servers = config["mcpServers"]

        legacy_key = "binary_ninja_mcp_max"
        existing_env = {}
        try:
            existing_env.update(servers.get(server_key, {}).get("env", {}))
        except Exception:
            existing_env = {}
        if legacy_key in servers:
            try:
                existing_env.update(servers[legacy_key].get("env", {}))
            except Exception:
                pass

        merged_env = dict(env)
        merged_env.update(existing_env)

        servers[server_key] = build_mcp_server_config(
            prefer_uv=prefer_uv,
            dev=dev_mode,
            repo_root=_repo_root(),
            server_url=server_url,
            env=merged_env,
            fallback_command=command,
            fallback_args=bridge_args,
        )

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            modified += 1
        except Exception:
            # Best-effort; skip failures silently in plugin context
            pass

    # Only write sentinel if we successfully modified at least one config
    if modified > 0:
        try:
            with open(sentinel, "w", encoding="utf-8") as f:
                f.write("ok")
        except Exception:
            pass

    return modified
