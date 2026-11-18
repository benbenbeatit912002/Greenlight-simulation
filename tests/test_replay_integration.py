import csv
import io
import os
import unittest
import zipfile
from pathlib import Path

from backend.application import SimulatorApplication
from backend.model_defaults import CONTROL_NAMES
from backend.weather_upload import AMSTERDAM_COLUMNS, validate_weather_workbook
from examples.taipei_heating_replay import daily_plan
from scripts.replay_run import read_bundle, replay
from tests.weather_fixtures import workbook_bytes

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.getenv("RUN_GREENLIGHT_INTEGRATION") == "1", "Opt-in full-model replay")
class ReplayIntegrationTests(unittest.TestCase):
    def test_export_replay_past_display_limit_and_edits(self):
        from backend.greenlight_adapter import GreenLightGymAdapter

        app = SimulatorApplication(GreenLightGymAdapter(), requested_engine="greenlight2")
        try:
            snap = app.reset(
                {"scenario": "spring", "seed": 17, "mode": "auto", "schedule": daily_plan("04:00")}
            )["snapshot"]
            app.step({"mode": "auto", "steps": 99})
            controls = dict.fromkeys(CONTROL_NAMES, 0.0)
            controls["uVent"] = 0.3
            app.step(
                {"mode": "manual", "controls": controls, "targets": {"nightTemp": 18}, "steps": 3}
            )
            end = app.step({"mode": "schedule", "steps": 2})["snapshot"]
            blob = app.export({"expectedRevision": app.revision, "runId": snap["runId"]})
            recipe = read_bundle(blob)
            self.assertEqual(
                recipe["calendar"],
                {
                    "sourceYear": 2010,
                    "timeConvention": "bundled-source-clock",
                    "start": "2010-03-01T00:00",
                    "plannedEnd": "2010-04-30T00:15",
                    "capturedEnd": "2010-03-02T02:00",
                },
            )
            with zipfile.ZipFile(io.BytesIO(blob)) as z:
                rows = list(csv.DictReader(io.StringIO(z.read("timeseries.csv").decode())))
            self.assertEqual(len(end["history"]), 97)
            self.assertEqual(len(rows), 105)
            self.assertAlmostEqual(
                float(rows[0]["fruit_dry_mass_g_m2"]), float(rows[0]["state_x25"]) / 1000
            )
            self.assertEqual(rows[0]["requested_uVent"], "")
            self.assertEqual(rows[100]["preceding_mode"], "manual")
            self.assertAlmostEqual(float(rows[100]["requested_uVent"]), 0.3, places=6)
            self.assertEqual([s["steps"] for s in recipe["commands"]], [99, 3, 2])
            verified, _ = replay(recipe)
            self.assertEqual(verified["climateMetrics"], end["climateMetrics"])
            legacy = {k: v for k, v in recipe.items() if k != "calendar"}
            legacy["format"] = "greenlight-run/1"
            self.assertEqual(replay(legacy)[0]["modelStep"], 104)
            wrong = {
                **recipe,
                "calendar": {**recipe["calendar"], "capturedEnd": "2010-03-04T12:00"},
            }
            with self.assertRaisesRegex(ValueError, "calendar"):
                replay(wrong)
            with self.assertRaisesRegex(ValueError, "modelVersion"):
                replay({**recipe, "identity": {**recipe["identity"], "modelVersion": "other"}})
        finally:
            app.close()

    def test_uploaded_weather_must_match_no_stale_server_ids(self):
        from backend.greenlight_adapter import GreenLightGymAdapter

        weather = (ROOT / "templates/weather-taipei-summer.xlsx").read_bytes()
        records = validate_weather_workbook(weather, include_records=True)["_records"]
        app = SimulatorApplication(GreenLightGymAdapter(), requested_engine="greenlight2")
        try:
            start = records[0]["time"]
            weather_id = app.stage_weather(records)["weatherId"]
            app.reset(
                {
                    "scenario": "uploaded",
                    "weatherId": weather_id,
                    "runWindow": {
                        "sourceYear": 2023,
                        "timeConvention": "source-local-standard",
                        "startSeconds": start,
                        "endSeconds": start + 1800,
                    },
                }
            )
            app.step({"mode": "auto", "steps": 1})
            recipe = read_bundle(app.engine.archive.bundle())
            self.assertNotIn("weatherId", recipe["reset"])
            self.assertEqual(
                recipe["calendar"],
                {
                    "sourceYear": 2023,
                    "timeConvention": "source-local-standard",
                    "start": "2023-07-15T00:00",
                    "plannedEnd": "2023-07-15T00:30",
                    "capturedEnd": "2023-07-15T00:15",
                },
            )
            with self.assertRaisesRegex(ValueError, "workbook"):
                replay(recipe)
            replaced = {
                **recipe,
                "identity": {**recipe["identity"], "weatherFingerprint": "c" * 64},
            }
            with self.assertRaisesRegex(ValueError, "weatherFingerprint"):
                replay(replaced, weather)
            # One forcing value an hour after initialization, beyond the 15-minute run
            # but inside the model's 12-hour look-ahead. No observed interval is changed.
            changed = [dict(row) for row in records]
            later = next(row for row in changed if row["time"] == start + 3600)
            later["wind speed"] += 1.0
            variant = workbook_bytes(
                [[row[k] for k in AMSTERDAM_COLUMNS] for row in changed],
                headers=AMSTERDAM_COLUMNS,
                dimension=f"A1:I{len(changed) + 1}",
            )
            with self.assertRaisesRegex(ValueError, "weatherFingerprint"):
                replay(recipe, variant)
            self.assertEqual(replay(recipe, weather)[0]["modelStep"], 1)
        finally:
            app.close()
