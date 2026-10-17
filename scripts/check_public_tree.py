"""Fail if local-only notes, environments or common credentials enter the Git index."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOTS = {
    ".venv",
    ".runtime",
    ".uv-cache",
    ".npm-cache",
    "node_modules",
    "worklogs",
    "user_data",
    "outputs",
    ".codex",
    ".agents",
}
PRIVATE_NAMES = {
    "AGENTS.md",
    "AGENTS.override.md",
    "SECOND_COMPUTER_PROMPT.md",
    "IMPLEMENTATION_PLAN.md",
    "PRODUCT_STRATEGY.md",
    ".env",
}
SECRET = re.compile(
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"
)


def inspect_paths(paths):
    problems = []
    for name in paths:
        path = PurePosixPath(name)
        if (
            path.parts[0] in PRIVATE_ROOTS
            or path.name in PRIVATE_NAMES
            or "__pycache__" in path.parts
            or path.suffix in {".pyc", ".pyo", ".log"}
            or name.startswith(
                ("frontend/legacy/", "data/weather/downloads/", "data/weather/reports/")
            )
            or name == "tests/browser_model_contract.test.js"
        ):
            problems.append(f"Local-only file is tracked: {name}")
    return problems


def inspect_index_content(paths):
    problems = []
    for name in paths:
        # Read the staged blob, not a potentially different unstaged working copy.
        result = subprocess.run(
            ["git", "show", f":{name}"], cwd=ROOT, capture_output=True, check=True
        )
        if SECRET.search(result.stdout):
            problems.append(f"Possible credential in staged file: {name}")
    return problems


def main():
    if not (ROOT / ".git").exists():
        print(
            "Public tree check skipped: no Git metadata at this project root. Run in a checkout to audit staged files."
        )
        return 0
    result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    paths = [p for p in result.stdout.decode("utf-8").split("\0") if p]
    if not paths:
        raise RuntimeError("No tracked files found; the Git audit cannot pass an empty index.")
    problems = inspect_paths(paths) + inspect_index_content(paths)
    for problem in problems:
        print(problem)
    if not problems:
        print(
            f"Public tree check: {len(paths)} tracked files; no local-only files or common key patterns."
        )
    return bool(problems)


if __name__ == "__main__":
    raise SystemExit(main())
