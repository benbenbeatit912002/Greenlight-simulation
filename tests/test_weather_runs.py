from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from backend.application import ApiError, SimulatorApplication
from examples.collect_weather import ROOT, json_bytes, save_new
from examples.weather_runs import ModelRunError, load_year, run_steps
from scripts import check_weather_archive

IDENTITY = {
    "modelVersion": "test-model",
    "weatherFingerprint": "weather-hash",
    "initialStateFingerprint": "initial-hash",
    "configurationFingerprint": "config-hash",
    "runWindow": {"totalSteps": 4},
    "resources": {"heatKwh": 0, "lampKwh": 0, "co2Kg": 0},
}


class WeatherRunTests(unittest.TestCase):
    def test_step_failure_keeps_reset_provenance(self):
        adapter = Mock()
        adapter.reset.return_value = IDENTITY
        adapter.step.side_effect = RuntimeError("solver failed")
        with self.assertRaises(ModelRunError) as caught:
            run_steps(adapter, {})
        for key in (
            "modelVersion",
            "weatherFingerprint",
            "initialStateFingerprint",
            "configurationFingerprint",
        ):
            self.assertEqual(caught.exception.evidence[key], IDENTITY[key])
        self.assertEqual(caught.exception.evidence["completedSteps"], 0)

    def test_batch_preserves_success_when_later_archive_is_missing(self):
        with (
            patch(
                "sys.argv",
                ["check", "--site", "amsterdam-nl", "--months", "1", "--collection", "fresh"],
            ),
            patch("scripts.check_weather_archive.new_adapter") as factory,
            patch(
                "scripts.check_weather_archive.load_year",
                side_effect=[([], {"source": {"sha256": "source"}}), FileNotFoundError("missing")],
            ) as load,
            patch("scripts.check_weather_archive.prepare_request", return_value={}),
            patch("scripts.check_weather_archive.run_steps", return_value=([], {"steps": 288})),
            patch("scripts.check_weather_archive.save_new") as save,
            patch("builtins.print"),
        ):
            self.assertEqual(check_weather_archive.main(), 1)
        report = json.loads(save.call_args.args[1])
        self.assertEqual([r["status"] for r in report["runs"]], ["completed", "failed"])
        self.assertEqual(report["runs"][1]["stage"], "weather")
        self.assertEqual(report["collection"], "fresh")
        self.assertTrue(all(call.kwargs["collection"] == "fresh" for call in load.call_args_list))
        factory.return_value.close.assert_called_once()

    def test_batch_keeps_failed_model_identity(self):
        failure = ModelRunError(
            "solver failed", {"modelVersion": "known-model", "completedSteps": 44}
        )
        with (
            patch(
                "sys.argv", ["check", "--site", "amsterdam-nl", "--months", "1", "--years", "2023"]
            ),
            patch("scripts.check_weather_archive.new_adapter"),
            patch(
                "scripts.check_weather_archive.load_year",
                return_value=([], {"source": {"sha256": "source"}}),
            ),
            patch("scripts.check_weather_archive.prepare_request", return_value={}),
            patch("scripts.check_weather_archive.run_steps", side_effect=failure),
            patch("scripts.check_weather_archive.save_new") as save,
            patch("builtins.print"),
        ):
            self.assertEqual(check_weather_archive.main(), 1)
        record = json.loads(save.call_args.args[1])["runs"][0]
        self.assertEqual(record["modelVersion"], "known-model")
        self.assertEqual(record["completedSteps"], 44)
        self.assertEqual(record["stage"], "simulation")

    def test_loader_uses_selected_collection(self):
        runtime = ROOT / ".runtime"
        runtime.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=runtime) as temp:
            with (
                patch("examples.collect_weather.DATA", Path(temp)),
                patch(
                    "examples.weather_runs.convert_hourly",
                    side_effect=lambda payload, year: [payload],
                ),
            ):
                for name in ("first", "second"):
                    folder = Path(temp) / "downloads" / name / "sample" / "2023"
                    raw, csv = json_bytes({"collection": name}), b"fixture\n"
                    save_new(folder / "source.json", raw)
                    save_new(folder / "hourly.csv", csv)
                    save_new(
                        folder / "manifest.json",
                        json_bytes(
                            {
                                "source": {"sha256": hashlib.sha256(raw).hexdigest()},
                                "hourlySha256": hashlib.sha256(csv).hexdigest(),
                            }
                        ),
                    )
                self.assertEqual(
                    load_year("sample", 2023, collection="first")[0][0]["collection"], "first"
                )
                self.assertEqual(
                    load_year("sample", 2023, collection="second")[0][0]["collection"], "second"
                )

    def test_documented_api_bounds_match_validator(self):
        card = (ROOT / "MODEL_CARD.md").read_text(encoding="utf-8")
        for key, low, high, text in (
            ("dayTemp", 10, 35, "10–35"),
            ("nightTemp", 8, 30, "8–30"),
            ("co2", 300, 1600, "300–1600"),
            ("maxRh", 40, 98, "40–98"),
        ):
            self.assertIn(text, card)
            for value in (low, high):
                SimulatorApplication._validate_targets({key: value})
            for value in (low - 1, high + 1):
                with self.assertRaises(ApiError):
                    SimulatorApplication._validate_targets({key: value})


if __name__ == "__main__":
    unittest.main()
