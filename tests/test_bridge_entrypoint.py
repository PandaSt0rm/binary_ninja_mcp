import json
import os
import subprocess
import sys
from pathlib import Path


def _with_src_on_pythonpath(env: dict, src: Path) -> dict:
    env = dict(env)
    existing = env.get("PYTHONPATH")
    if existing:
        env["PYTHONPATH"] = f"{src}{os.pathsep}{existing}"
    else:
        env["PYTHONPATH"] = str(src)
    return env


def test_bridge_entrypoint_module_executes():
    repo_root = Path(__file__).resolve().parents[1]
    src = repo_root / "src"
    env = _with_src_on_pythonpath(os.environ, src)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "binary_ninja_mcp.bridge.binja_mcp_bridge",
            "--config",
            "--no-uv",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "mcpServers" in payload
