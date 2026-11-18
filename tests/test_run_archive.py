import csv
import io
import json
import stat
import threading
import unittest
import zipfile
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib import error, request

from backend.application import ApiError, SimulatorApplication
from backend.climate_metrics import DEFAULT_LIMITS
from backend.model_defaults import DEFAULT_TARGETS
from backend.run_archive import COLUMNS, RunArchive
from backend.server import create_server, local_export_origin
from scripts.replay_run import (
    FINGERPRINTS,
    ROOT,
    project_destination,
    read_bundle,
    validate_identity,
    validate_recipe,
)


def archive():
    return RunArchive(
        {
            "scenario": "spring",
            "mode": "auto",
            "targets": DEFAULT_TARGETS,
            "seed": 42,
            "greenhouseConfig": {"schemaVersion": 1, "overrides": {}},
            "evaluationLimits": DEFAULT_LIMITS,
        },
        {
            **dict.fromkeys(FINGERPRINTS, "a" * 64),
            "modelVersion": "gl-gym2@0.3.2+sha256." + "b" * 64 + ".adapter.test.params." + "a" * 64,
            "costModelId": "greenlight-gym2-variable-costs",
        },
    )


def point(a, n, command):
    a.append(n, [0] * (len(COLUMNS) - 1), command)


class RunArchiveTests(unittest.TestCase):
    def test_unused_schedule_not_disclosed_but_later_scheduled_steps_are_supported(self):
        a = archive()
        a.reset["schedule"] = {
            "schemaVersion": 1,
            "entries": [
                {
                    "time": "00:00",
                    "controls": {
                        k: 0.0 for k in ("uBoil", "uCO2", "uThScr", "uVent", "uLamp", "uBlScr")
                    },
                }
            ],
        }
        point(a, 0, None)
        point(a, 1, {"mode": "auto", "targets": DEFAULT_TARGETS})
        self.assertNotIn("schedule", read_bundle(a.bundle())["reset"])
        point(a, 2, {"mode": "schedule", "targets": DEFAULT_TARGETS})
        self.assertEqual(read_bundle(a.bundle())["reset"]["schedule"], a.reset["schedule"])

    def test_no_success_without_concrete_source_and_complete_fingerprints(self):
        identity = archive().identity
        validate_identity(identity)
        git = {
            **identity,
            "modelVersion": identity["modelVersion"].replace(
                "sha256." + "b" * 64, "git." + "d" * 40
            ),
        }
        validate_identity({**git, "sourceSha256": "c" * 64})
        for altered in (
            git,
            {k: v for k, v in identity.items() if k != "weatherFingerprint"},
            {**identity, "modelVersion": identity["modelVersion"].replace("b" * 64, "unversioned")},
            {**identity, "initialStateFingerprint": ""},
        ):
            with self.subTest(altered=altered), self.assertRaises(ValueError):
                validate_identity(altered)

    def test_private_download_requires_local_peer_host_and_matching_origin(self):
        host = "localhost:5000"
        self.assertTrue(local_export_origin("127.0.0.1", host, None, 5000))
        self.assertTrue(local_export_origin("::1", host, "http://localhost:5000", 5000))
        for peer, name, origin in (
            ("192.0.2.1", host, None),
            ("127.0.0.1", "example.invalid", None),
            ("::1", host, "https://example.invalid"),
        ):
            self.assertFalse(local_export_origin(peer, name, origin, 5000))

    def test_generated_outputs_are_project_relative_and_links_are_refused(self):
        self.assertEqual(project_destination("new-output.zip"), ROOT / "new-output.zip")
        for bad in (ROOT, ROOT.parent / "elsewhere.zip", "../elsewhere.zip", ".git/note", "NUL"):
            with self.assertRaises(ValueError):
                project_destination(bad)
        original = Path.lstat

        def simulated_junction(path):
            if path.name == "linked-target":
                return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
            return original(path)

        with (
            patch.object(Path, "lstat", simulated_junction),
            self.assertRaisesRegex(ValueError, "Linked"),
        ):
            project_destination("linked-target/output.zip")

    def test_http_download_is_private_versioned_and_read_only(self):
        a = archive()
        point(a, 0, None)
        point(a, 1, {"mode": "auto", "targets": DEFAULT_TARGETS})
        server = create_server(port=0, engine=SimpleNamespace(archive=a, run_id="my-run"))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/api/run/export"

            def post(revision):
                body = json.dumps({"expectedRevision": revision, "runId": "my-run"}).encode()
                return request.urlopen(
                    request.Request(url, data=body, headers={"Content-Type": "application/json"}),
                    timeout=3,
                )

            with post(0) as response:
                self.assertEqual(response.headers.get_content_type(), "application/zip")
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                self.assertIn("attachment;", response.headers["Content-Disposition"])
                self.assertEqual(read_bundle(response.read())["completedSteps"], 1)
            with self.assertRaises(error.HTTPError) as stale:
                post(1)
            with stale.exception as response:
                self.assertEqual(response.code, 409)
            self.assertEqual(server.application.revision, 0)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_replay_guides_are_served_by_explicit_public_paths(self):
        server = create_server(port=0, engine=None)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for name in ("user-guide", "greenhouse-measurements", "scientific-validation"):
                url = f"http://127.0.0.1:{server.server_port}/docs/{name}.md"
                with self.subTest(name=name), request.urlopen(url, timeout=3) as response:
                    self.assertEqual(response.status, 200)
                    self.assertTrue(response.read().startswith(b"# "))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_every_point_survives_with_commands_by_value(self):
        a = archive()
        targets = dict(DEFAULT_TARGETS)
        point(a, 0, None)
        for i in range(1, 104):
            if i == 102:
                targets["dayTemp"] = 23.0
            point(a, i, {"mode": "auto", "targets": targets})
        blob = a.bundle()
        recipe = read_bundle(blob)
        self.assertEqual([c["steps"] for c in recipe["commands"]], [101, 2])
        self.assertEqual(recipe["commands"][0]["command"]["targets"]["dayTemp"], 21.5)
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            rows = list(csv.DictReader(io.StringIO(z.read("timeseries.csv").decode())))
        self.assertEqual([int(r["step"]) for r in rows], list(range(104)))

    def test_no_stale_export_no_revision_mutation(self):
        a = archive()
        engine = SimpleNamespace(archive=a, run_id="current")
        app = SimulatorApplication(engine, requested_engine="test")
        point(a, 0, None)
        payload = {"runId": "current", "expectedRevision": 0}
        for change in ({}, {"runId": "old"}, {"expectedRevision": 1}, {"expectedRevision": None}):
            with self.subTest(change=change), self.assertRaises(ApiError):
                app.export({**payload, **change})
        point(a, 1, {"mode": "auto", "targets": DEFAULT_TARGETS})
        self.assertEqual(read_bundle(app.export(payload))["completedSteps"], 1)
        self.assertEqual(app.revision, 0)

    def test_incomplete_or_unexpected_recipe_is_not_replayed(self):
        a = archive()
        point(a, 0, None)
        point(a, 1, {"mode": "auto", "targets": DEFAULT_TARGETS})
        saved = read_bundle(a.bundle())
        for change in (
            {"completedSteps": True},
            {"completedSteps": 2},
            {"completedSteps": 1000000},
            {"commands": []},
            {"format": "wrong"},
            {"reset": {**saved["reset"], "_prepared_weather": {}}},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_recipe({**deepcopy(saved), **change})
        altered = io.BytesIO()
        with zipfile.ZipFile(altered, "w") as z:
            z.writestr("settings.json", json.dumps(saved))
            z.writestr("timeseries.csv", "different bytes")
        with self.assertRaisesRegex(ValueError, "checksum"):
            read_bundle(altered.getvalue())
        with self.assertRaises(ValueError):
            point(a, 9, {"mode": "auto", "targets": DEFAULT_TARGETS})
