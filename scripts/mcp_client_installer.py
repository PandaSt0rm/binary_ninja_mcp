import argparse
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Import shared utilities
from binary_ninja_mcp.config import (  # noqa: E402
    SERVER_NAME,
    build_mcp_server_config,
    resolve_server_url,
)
from binary_ninja_mcp.plugin.utils.python_detection import (  # noqa: E402
    copy_python_env,
    create_venv_with_system_python,
    get_python_executable,
)

MCP_SERVER_KEY = SERVER_NAME


def _repo_root() -> str:
    """Return the repository root (one level above this scripts directory)."""
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def _bridge_module_args() -> list[str]:
    return ["-m", "binary_ninja_mcp.bridge.binja_mcp_bridge"]


def _venv_dir() -> str:
    return os.path.join(_repo_root(), ".venv")


def _venv_python() -> str:
    d = _venv_dir()
    if sys.platform == "win32":
        # Always prefer a real Python interpreter for MCP stdio servers.
        # "binaryninja.exe" is an embedded interpreter launcher and does not
        # behave like a normal Python on stdio, causing MCP clients to fail.
        py = os.path.join(d, "Scripts", "python.exe")
        return py
    return os.path.join(d, "bin", "python3")


def ensure_local_venv() -> str:
    """Create a local venv under the plugin root if missing and return its python."""
    vdir = _venv_dir()
    req = os.path.join(_repo_root(), "src", "binary_ninja_mcp", "bridge", "requirements.txt")

    try:
        py = create_venv_with_system_python(vdir, req if os.path.exists(req) else None)
        return py if os.path.exists(py) else get_python_executable()
    except Exception:
        return get_python_executable()


# Note: get_python_executable and copy_python_env are now imported from utils.python_detection


def print_mcp_config(*, prefer_uv: bool = True, dev: bool = False, server_url: str | None = None):
    """Print a generic MCP config snippet users can copy to unsupported clients."""
    env: dict[str, str] = {}
    copy_python_env(env)
    python = ensure_local_venv()
    mcp_config = build_mcp_server_config(
        prefer_uv=prefer_uv,
        dev=dev,
        repo_root=_repo_root(),
        server_url=server_url,
        env=env,
        fallback_command=python,
        fallback_args=_bridge_module_args(),
    )
    print(json.dumps({"mcpServers": {MCP_SERVER_KEY: mcp_config}}, indent=2))


def _config_targets() -> dict[str, tuple[str, str]]:
    """Return supported MCP client config locations per platform.

    Value is (config_dir, filename).
    """
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


def install_mcp_servers(
    *,
    uninstall: bool = False,
    quiet: bool = False,
    env: dict[str, str] | None = None,
    prefer_uv: bool = True,
    dev: bool = False,
    server_url: str | None = None,
) -> int:
    """Install or remove MCP server entries for supported clients.

    Returns the number of configs modified.
    """
    env = {} if env is None else dict(env)
    server_url = resolve_server_url(server_url)
    targets = _config_targets()
    if not targets:
        if not quiet:
            print(f"Unsupported platform: {sys.platform}")
        return 0

    installed = 0
    for name, (config_dir, config_file) in targets.items():
        config_path = os.path.join(config_dir, config_file)
        action_word = "uninstall" if uninstall else "installation"

        if not os.path.exists(config_dir):
            if not quiet:
                print(f"Skipping {name} {action_word}\n  Config: {config_path} (not found)")
            continue

        if not os.path.exists(config_path):
            config: dict = {}
        else:
            try:
                with open(config_path, encoding="utf-8") as f:
                    data = f.read().strip()
                    config = json.loads(data) if data else {}
            except json.decoder.JSONDecodeError:
                if not quiet:
                    print(f"Skipping {name} uninstall\n  Config: {config_path} (invalid JSON)")
                continue

        config.setdefault("mcpServers", {})
        mcp_servers = config["mcpServers"]

        if uninstall:
            if MCP_SERVER_KEY not in mcp_servers:
                if not quiet:
                    print(f"Skipping {name} uninstall\n  Config: {config_path} (not installed)")
                continue
            del mcp_servers[MCP_SERVER_KEY]
        else:
            # Preserve any existing env overrides for this server
            if MCP_SERVER_KEY in mcp_servers:
                for key, value in mcp_servers[MCP_SERVER_KEY].get("env", {}).items():
                    env.setdefault(key, value)

            if copy_python_env(env) and not quiet:
                print("[WARNING] Custom Python environment variables detected")

            python = ensure_local_venv()
            server_cfg = build_mcp_server_config(
                prefer_uv=prefer_uv,
                dev=dev,
                repo_root=_repo_root(),
                server_url=server_url,
                env=env,
                fallback_command=python,
                fallback_args=_bridge_module_args(),
            )
            mcp_servers[MCP_SERVER_KEY] = server_cfg

        # Write back
        os.makedirs(config_dir, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        if not quiet:
            print(
                ("Uninstalled" if uninstall else "Installed")
                + f" {name} MCP server (restart required)\n  Config: {config_path}"
            )
        installed += 1

    if not uninstall and installed == 0 and not quiet:
        print("No MCP servers installed. For unsupported MCP clients, use the following config:\n")
        print_mcp_config(prefer_uv=prefer_uv, dev=dev, server_url=server_url)

    return installed


def main():
    parser = argparse.ArgumentParser(
        description="Binary Ninja MCP Max - MCP Client Installer (CLI)"
    )
    parser.add_argument(
        "--install", action="store_true", help="Install MCP server entries for supported clients"
    )
    parser.add_argument(
        "--uninstall", action="store_true", help="Remove MCP server entries from supported clients"
    )
    parser.add_argument("--config", action="store_true", help="Print generic MCP config JSON")
    parser.add_argument("--quiet", action="store_true", help="Reduce output noise")
    parser.add_argument(
        "--dev", action="store_true", help="Use 'uv run' from the repo root for MCP config"
    )
    parser.add_argument(
        "--no-uv", action="store_true", help="Disable uv/uvx preference in generated configs"
    )
    parser.add_argument("--server", help="Binary Ninja MCP HTTP server URL")
    parser.add_argument("--host", help="Binary Ninja MCP HTTP server host")
    parser.add_argument("--port", type=int, help="Binary Ninja MCP HTTP server port")
    args = parser.parse_args()

    prefer_uv = not args.no_uv
    server_url = resolve_server_url(args.server, args.host, args.port)

    if args.install and args.uninstall:
        print("Cannot install and uninstall at the same time")
        return

    if args.config:
        print_mcp_config(prefer_uv=prefer_uv, dev=args.dev, server_url=server_url)
        return

    if args.uninstall:
        install_mcp_servers(uninstall=True, quiet=args.quiet)
        # Also remove auto-setup sentinel so the plugin can re-run setup later
        sentinel = os.path.join(_repo_root(), ".mcp_auto_setup_done")
        try:
            os.remove(sentinel)
            if not args.quiet:
                print(f"Removed auto-setup marker: {sentinel}")
        except FileNotFoundError:
            pass
        except Exception as e:
            if not args.quiet:
                print(f"Warning: failed to remove auto-setup marker: {e}")
        return

    # Default action is install if no flag is provided
    if args.install or (not args.uninstall and not args.config):
        install_mcp_servers(
            quiet=args.quiet,
            prefer_uv=prefer_uv,
            dev=args.dev,
            server_url=server_url,
        )


if __name__ == "__main__":
    main()
