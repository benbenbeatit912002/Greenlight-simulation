"""Run the same repository checks locally and in CI, without external model data."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    runtime = ROOT / ".runtime"
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["RUN_GREENLIGHT_INTEGRATION"] = "0"
    for name, folder in {
        "TEMP": "tmp",
        "TMP": "tmp",
        "MPLCONFIGDIR": "matplotlib",
        "XDG_CACHE_HOME": "cache",
    }.items():
        destination = runtime / folder
        destination.mkdir(parents=True, exist_ok=True)
        environment[name] = str(destination)
    environment["npm_config_cache"] = str(ROOT / ".npm-cache")
    node = shutil.which("node")
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not node or not npm:
        print("Install Node.js 22 or later (including npm), then run npm ci.", file=sys.stderr)
        return 2
    python = [sys.executable, "-B"]
    commands = [
        [*python, "-m", "ruff", "check", "backend", "tests", "scripts", "examples", "server.py"],
        [
            *python,
            "-m",
            "ruff",
            "format",
            "--check",
            "backend",
            "tests",
            "scripts",
            "examples",
            "server.py",
        ],
        [npm, "run", "format:check"],
        *[[node, "--check", str(path)] for path in sorted((ROOT / "frontend").rglob("*.js"))],
        [*python, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"],
        [npm, "test"],
        [*python, "examples/validate_weather.py"],
    ]
    for command in commands:
        print("\n> " + " ".join(command), flush=True)
        result = subprocess.run(command, cwd=ROOT, env=environment, check=False)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
