from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from scripts.check_public_tree import inspect_index_content, inspect_paths


class PublicTreeTests(unittest.TestCase):
    def test_rejects_private_runtime_and_retired_files(self):
        paths = [
            "AGENTS.md",
            ".env",
            ".runtime/log.json",
            "worklogs/index.html",
            "data/weather/downloads/site/source.json",
            "data/weather/reports/results.json",
            "frontend/legacy/simulator-engine.js",
            "tests/browser_model_contract.test.js",
        ]
        self.assertEqual(len(inspect_paths(paths)), len(paths))

    def test_rejects_environment_variants_and_generated_files(self):
        paths = [
            ".env.local",
            ".env.production",
            "frontend/.env.test",
            "docs/.DS_Store",
            "docs/images/Thumbs.db",
            "examples/.ipynb_checkpoints/demo-checkpoint.ipynb",
            "server.log",
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(inspect_paths([path]), [f"Local-only file is tracked: {path}"])

    def test_keeps_useful_sources_tests_docs_and_samples(self):
        self.assertEqual(
            inspect_paths(
                [
                    "README.md",
                    "backend/weather_archive.py",
                    "tests/test_weather_archive.py",
                    "data/weather/sites.json",
                    "templates/weather-taipei-summer.xlsx",
                    "docs/images/greenhouse-dashboard.jpg",
                    "pyproject.toml",
                    "uv.lock",
                    "package-lock.json",
                    ".github/workflows/ci.yml",
                    "SECURITY.md",
                    "CONTRIBUTING.md",
                    "CITATION.md",
                ]
            ),
            [],
        )

    def test_credential_scan_reads_index_without_printing_contents(self):
        token = b"ghp_" + b"x" * 36
        with patch(
            "scripts.check_public_tree.subprocess.run",
            return_value=subprocess.CompletedProcess([], 0, token),
        ) as run:
            problems = inspect_index_content(["sample.txt"])
        self.assertEqual(run.call_args.args[0], ["git", "show", ":sample.txt"])
        self.assertEqual(problems, ["Possible credential in staged file: sample.txt"])
        self.assertNotIn(token.decode(), str(problems))


if __name__ == "__main__":
    unittest.main()
