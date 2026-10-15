"""Resolve the installed model or an explicit, read-only source override."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import sys
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_MODEL_VERSION = "0.3.2"
INSTALL_HINT = "uv sync --locked --extra greenlight --python 3.12 --cache-dir .uv-cache"


@dataclass(frozen=True)
class ModelSource:
    root: Path
    version: str
    kind: str


def resolve_model_source(source_path: str | Path | None = None) -> ModelSource:
    configured = source_path if source_path is not None else os.environ.get("GREENLIGHT_GYM_PATH")
    if configured:
        return ModelSource(
            Path(configured).expanduser().resolve(), "local-source", "source-checkout"
        )
    try:
        distribution = importlib.metadata.distribution("gl-gym")
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError(
            f"GreenLight model is not installed. Run: {INSTALL_HINT}. "
            "Advanced users can set GREENLIGHT_GYM_PATH to a compatible source checkout."
        ) from exc
    if distribution.version != SUPPORTED_MODEL_VERSION:
        raise RuntimeError(
            f"Expected gl-gym {SUPPORTED_MODEL_VERSION}, found {distribution.version}. "
            f"Restore the tested environment with: {INSTALL_HINT}"
        )
    root = Path(distribution.locate_file("gl_gym/__init__.py")).resolve().parents[1]
    return ModelSource(root, distribution.version, "installed-package")


def default_source_path() -> Path:
    return resolve_model_source().root


def verify_loaded_model_source(root: Path) -> None:
    """Do not combine modules from two model installations in one process."""
    package = root / "gl_gym"
    for name, module in tuple(sys.modules.items()):
        if name != "gl_gym" and not name.startswith("gl_gym."):
            continue
        filename = getattr(module, "__file__", None)
        if not filename or not Path(filename).resolve().is_relative_to(package):
            raise RuntimeError(
                "A different gl_gym source is already loaded. Restart Python after changing "
                "GREENLIGHT_GYM_PATH; model sources cannot be mixed in one process."
            )


def prepare_model_import(root: Path) -> None:
    """Select and verify the package origin before any model code executes."""
    expected = root / "gl_gym" / "__init__.py"
    if not expected.is_file():
        raise RuntimeError(f"GL-Gym2 source not found at {root}")
    verify_loaded_model_source(root)
    source_text = str(root)
    sys.path[:] = [source_text, *(entry for entry in sys.path if entry != source_text)]
    sys.dont_write_bytecode = True
    if "gl_gym" not in sys.modules:
        spec = importlib.util.find_spec("gl_gym")
        if spec is None or spec.origin is None or Path(spec.origin).resolve() != expected.resolve():
            raise RuntimeError(
                "Python resolved an unexpected gl_gym source. Check the environment."
            )
