"""Read-only source and array fingerprints used to compare runs."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def _git_revision(source_path: Path) -> str | None:
    options: dict[str, Any] = {}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        result = subprocess.run(
            ["git", "-C", str(source_path), "rev-parse", "--verify", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
            **options,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    revision = result.stdout.strip().lower()
    if len(revision) != 40 or any(character not in "0123456789abcdef" for character in revision):
        return None
    return revision


def _loaded_source_fingerprint(source_path: Path) -> str | None:
    source_files: set[Path] = set()
    for module_name, module in tuple(sys.modules.items()):
        if module_name != "gl_gym" and not module_name.startswith("gl_gym."):
            continue
        file_name = getattr(module, "__file__", None)
        if not file_name:
            continue
        module_path = Path(file_name)
        if module_path.suffix in {".pyc", ".pyo"}:
            try:
                module_path = Path(importlib.util.source_from_cache(str(module_path)))
            except ValueError:
                continue
        try:
            resolved = module_path.resolve()
            resolved.relative_to(source_path)
        except (OSError, ValueError):
            continue
        if resolved.suffix == ".py" and resolved.is_file():
            source_files.add(resolved)

    if not source_files:
        return None

    digest = hashlib.sha256()
    for source_file in sorted(source_files, key=lambda path: path.as_posix()):
        relative_path = source_file.relative_to(source_path).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        with source_file.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def _array_fingerprint(np_module: Any, values: Any) -> str | None:
    try:
        array = np_module.ascontiguousarray(values)
    except Exception:
        return None
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii", errors="replace"))
    digest.update(b"\0")
    digest.update(repr(tuple(array.shape)).encode("ascii"))
    digest.update(b"\0")
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()
