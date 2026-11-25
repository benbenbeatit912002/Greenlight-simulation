"""Equipment ownership, model execution, failure isolation and portable MPC replay."""

import os
import unittest
from unittest.mock import patch

from backend.application import ApiError, SimulatorApplication
from backend.model_defaults import CONTROL_NAMES
from backend.mpc_controller import MAX_MOVE, POLICY, MpcStopped, devices
from scripts.replay_run import read_bundle, replay, validate_recipe
from tests.test_api_server import FakeEngine


class MpcRequestTests(unittest.TestCase):
    def test_selection_is_unique_known_and_canonical(self):
        self.assertEqual(devices([]), ())
        self.assertEqual(devices(["uVent", "uBoil"]), ("uBoil", "uVent"))
        for invalid in (None, "uVent", ["heat"], [True], [{}], ["uVent", "uVent"]):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                devices(invalid)

    def test_rejected_requests_do_not_advance_revision(self):
        app = SimulatorApplication(FakeEngine(), requested_engine="auto")
        rev = app.revision
        for spec in (
            {"mode": "mpc"},
            {"mode": "mpc", "mpcDevices": ["uLamp", "uLamp"]},
            {"mode": "mpc", "mpcDevices": ["uBoil"], "mpcPolicy": "other"},
            {"mode": "auto", "mpcDevices": ["uBoil"]},
        ):
            with self.subTest(spec=spec), self.assertRaises(ApiError):
                app.reset(spec)
        with self.assertRaises(ApiError):
            app.step({"mpcDevices": ["uVent"]})
        self.assertEqual(app.revision, rev)


@unittest.skipUnless(os.getenv("RUN_GREENLIGHT_INTEGRATION") == "1", "Opt-in full model")
class MpcIntegrationTests(unittest.TestCase):
    def setUp(self):
        from backend.greenlight_adapter import GreenLightGymAdapter

        self.app = SimulatorApplication(GreenLightGymAdapter(), requested_engine="auto")
        self.addCleanup(self.app.close)

    def test_routing_and_empty_selection(self):
        app = self.app
        for group in (["uBoil", "uVent"], list(CONTROL_NAMES)):
            with self.subTest(group=group):
                snap = app.reset({"mode": "mpc", "mpcDevices": group})["snapshot"]
                self.assertEqual(snap["mpcPolicy"], POLICY)
                for _ in range(2):
                    rules = app.engine._controller_action()
                    prev = app.engine.core.u.copy()
                    s = app.step({"mode": "mpc"})["snapshot"]
                    for j, key in enumerate(CONTROL_NAMES):
                        got = s["controlHistory"][-1]["applied"][key]
                        if key not in group:
                            self.assertEqual(got, float(rules[j]))
                        else:
                            self.assertLessEqual(abs(got - prev[j]), MAX_MOVE + 1e-6)
                            self.assertTrue(0 <= got <= 1)
                    self.assertEqual(s["mode"], "mpc")
        empty = app.reset({"mode": "mpc", "mpcDevices": []})["snapshot"]
        self.assertEqual((empty["mode"], empty["mpcDevices"]), ("auto", []))
        mixed = app.step({})["snapshot"]
        app.reset({"mode": "auto"})
        auto = app.step({})["snapshot"]
        self.assertEqual(auto["indoor"], mixed["indoor"])
        self.assertEqual(auto["controls"], mixed["controls"])

    def test_failed_solve_and_changes_never_dispatch(self):
        app = self.app
        snap = app.reset({"mode": "mpc", "mpcDevices": ["uVent"]})["snapshot"]
        revision = app.revision
        for change in (
            {"mode": "auto"},
            {"steps": 2},
            {"targets": {"dayTemp": 25}},
            {"controls": dict.fromkeys(CONTROL_NAMES, 0.5)},
        ):
            with self.assertRaises(ApiError):
                app.step(change)
        with patch.object(app.engine.mpc, "action", side_effect=MpcStopped("No command.")):
            with self.assertRaises(ApiError) as raised:
                app.step({"steps": 1})
        self.assertEqual(raised.exception.code, "MPC_STOPPED")
        self.assertEqual(app.revision, revision)
        self.assertEqual(app.status()["snapshot"], snap)
        self.assertEqual(app.step({})["snapshot"]["modelStep"], 1)

    def test_export_really_replays_and_stops_at_one_remaining_interval(self):
        from pathlib import Path

        from backend.weather_upload import validate_weather_workbook

        app = self.app
        book = (
            Path(__file__).resolve().parents[1] / "templates/weather-taipei-summer.xlsx"
        ).read_bytes()
        records = validate_weather_workbook(book, include_records=True)["_records"]
        t = records[0]["time"]
        spec = {
            "mode": "mpc",
            "mpcDevices": ["uBoil"],
            "scenario": "uploaded",
            "weatherId": app.stage_weather(records)["weatherId"],
            "runWindow": {
                "sourceYear": 2023,
                "timeConvention": "source-local-standard",
                "startSeconds": t,
                "endSeconds": t + 1800,
            },
        }
        start = app.reset(spec)["snapshot"]
        for _ in range(2):
            end = app.step({})["snapshot"]
        self.assertEqual(set(app.engine.mpc.solvers), {1, 2})
        self.assertTrue(end["episode"]["terminated"])
        self.assertEqual(end["modelStep"], 2)
        recipe = read_bundle(
            app.export({"runId": start["runId"], "expectedRevision": app.revision})
        )
        self.assertEqual(recipe["reset"]["mpcDevices"], ["uBoil"])
        self.assertEqual(recipe["reset"]["mpcPolicy"], POLICY)
        self.assertEqual(replay(recipe, book)[0]["indoor"], end["indoor"])
        with self.assertRaises(ValueError):
            validate_recipe({**recipe, "reset": {**recipe["reset"], "mpcPolicy": "other"}})
        command = recipe["commands"][0]["command"]
        changed = {**command, "targets": {**command["targets"], "dayTemp": 25}}
        with self.assertRaisesRegex(ValueError, "targets"):
            validate_recipe({**recipe, "commands": [{"steps": 2, "command": changed}]})
