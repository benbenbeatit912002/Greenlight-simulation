"""Model discovery and preflight contracts without importing the scientific package."""

from __future__ import annotations

import importlib
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from backend.model_source import (
    prepare_model_import,
    resolve_model_source,
    verify_loaded_model_source,
)
from backend.provenance import _git_revision
from backend.server import main


def without_model_modules():
    return {
        name: module
        for name, module in sys.modules.items()
        if name != "gl_gym" and not name.startswith("gl_gym.")
    }


class ModelSourceTests(unittest.TestCase):
    def test_installed_distribution_is_resolved_without_importing_it(self):
        root = Path(".runtime/fake-site-packages").resolve()
        distribution = Mock(version="0.3.2")
        distribution.locate_file.return_value = root / "gl_gym" / "__init__.py"
        with (
            patch.dict(os.environ, {}, clear=True),
            patch(
                "backend.model_source.importlib.metadata.distribution", return_value=distribution
            ),
        ):
            source = resolve_model_source()
        self.assertEqual(source.root, root)
        self.assertEqual(source.version, "0.3.2")
        self.assertEqual(source.kind, "installed-package")

    def test_wrong_package_version_is_rejected(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            patch(
                "backend.model_source.importlib.metadata.distribution",
                return_value=Mock(version="9.0"),
            ),
            self.assertRaisesRegex(RuntimeError, "Expected gl-gym 0.3.2"),
        ):
            resolve_model_source()

    def test_source_override_never_claims_unrelated_installed_version(self):
        with (
            patch.dict(os.environ, {"GREENLIGHT_GYM_PATH": "chosen-model"}),
            patch("backend.model_source.importlib.metadata.distribution") as lookup,
        ):
            source = resolve_model_source()
            explicit = resolve_model_source("explicit-model")
        lookup.assert_not_called()
        self.assertEqual(source.root, Path("chosen-model").resolve())
        self.assertEqual(explicit.root, Path("explicit-model").resolve())
        self.assertEqual(source.version, "local-source")
        self.assertEqual(source.kind, "source-checkout")

    def test_mixed_loaded_sources_are_rejected(self):
        root = Path(".runtime/fake-site-packages").resolve()
        own = SimpleNamespace(__file__=str(root / "gl_gym" / "__init__.py"))
        other = SimpleNamespace(__file__=str(root / "other" / "weather.py"))
        with patch.dict(sys.modules, {**without_model_modules(), "gl_gym": own}, clear=True):
            verify_loaded_model_source(root)
            with patch.dict(sys.modules, {"gl_gym.components.weather": other}):
                with self.assertRaisesRegex(RuntimeError, "different gl_gym source"):
                    verify_loaded_model_source(root)

    def test_nested_package_does_not_inherit_application_git_revision(self):
        with patch.object(Path, "exists", return_value=False), patch("subprocess.run") as run:
            self.assertIsNone(_git_revision(Path(".runtime/fake-site-packages")))
        run.assert_not_called()

    def test_selected_source_takes_precedence_before_any_model_code_executes(self):
        runtime = Path(__file__).resolve().parents[1] / ".runtime" / "source-tests"
        runtime.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=runtime) as temporary:
            selected = Path(temporary) / "selected"
            competing = Path(temporary) / "competing"
            for root, content in (
                (selected, "MARKER = 'selected'\n"),
                (competing, "raise AssertionError('Wrong source executed')\n"),
            ):
                package = root / "gl_gym"
                package.mkdir(parents=True)
                (package / "__init__.py").write_text(content, encoding="utf-8")
            with (
                patch.object(sys, "path", [str(competing), *sys.path, str(selected)]),
                patch.dict(sys.modules, without_model_modules(), clear=True),
                patch.object(sys, "dont_write_bytecode", True),
            ):
                prepare_model_import(selected)
                self.assertNotIn("gl_gym", sys.modules)
                self.assertEqual(sys.path[0], str(selected))
                self.assertEqual(importlib.import_module("gl_gym").MARKER, "selected")

    def test_unexpected_import_origin_is_rejected_before_execution(self):
        root = Path(".runtime/fake-site-packages").resolve()
        with (
            patch.object(Path, "is_file", return_value=True),
            patch.object(sys, "path", list(sys.path)),
            patch.dict(sys.modules, without_model_modules(), clear=True),
            patch(
                "backend.model_source.importlib.util.find_spec",
                return_value=SimpleNamespace(origin=str(root / "other.py")),
            ),
            self.assertRaisesRegex(RuntimeError, "unexpected gl_gym source"),
        ):
            prepare_model_import(root)


class ModelCheckTests(unittest.TestCase):
    def fake_engine(self):
        engine = Mock()
        engine.step.return_value = {"modelStep": 1, "episode": {"truncated": False}}
        engine.metadata.return_value = {"version": "0.3.2", "scientific": True}
        engine._np.isfinite.return_value.all.return_value = True
        return engine

    def test_preflight_steps_closes_and_does_not_open_server(self):
        engine = self.fake_engine()
        with (
            patch("backend.server.GreenLightGymAdapter", return_value=engine),
            patch("backend.server.create_server") as server,
            redirect_stdout(io.StringIO()) as output,
        ):
            self.assertEqual(main(["--check-model"]), 0)
        engine.step.assert_called_once_with({"steps": 1, "mode": "auto"})
        engine.close.assert_called_once()
        server.assert_not_called()
        self.assertIn("check passed", output.getvalue())

    def test_preflight_reports_missing_model_without_starting_server(self):
        with (
            patch("backend.server.GreenLightGymAdapter", side_effect=RuntimeError("not installed")),
            patch("backend.server.create_server") as server,
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(main(["--check-model"]), 2)
        server.assert_not_called()

    def test_preflight_rejects_solver_and_nonfinite_failures_and_closes(self):
        for failure in ("truncated", "nonfinite", "bad-step"):
            with self.subTest(failure=failure):
                engine = self.fake_engine()
                if failure == "truncated":
                    engine.step.return_value["episode"]["truncated"] = True
                elif failure == "nonfinite":
                    engine._np.isfinite.return_value.all.return_value = False
                else:
                    engine.step.return_value["modelStep"] = 0
                with (
                    patch("backend.server.GreenLightGymAdapter", return_value=engine),
                    redirect_stdout(io.StringIO()),
                ):
                    self.assertEqual(main(["--check-model"]), 2)
                engine.close.assert_called_once()
