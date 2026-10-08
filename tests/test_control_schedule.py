from __future__ import annotations

import unittest
from copy import deepcopy

from backend.application import ApiError, SimulatorApplication
from backend.climate_metrics import DEFAULT_LIMITS, ClimateMetrics, validate_limits
from backend.control_schedule import scheduled_controls, validate_schedule
from backend.model_defaults import CONTROL_NAMES
from tests.test_api_server import FakeEngine


def recipe():
    return {
        "schemaVersion": 1,
        "entries": [
            {"time": "00:00", "controls": dict.fromkeys(CONTROL_NAMES, 0.0)},
            {"time": "06:00", "controls": dict.fromkeys(CONTROL_NAMES, 0.7)},
            {"time": "23:45", "controls": dict.fromkeys(CONTROL_NAMES, 1.0)},
        ],
    }


class ScheduleTests(unittest.TestCase):
    def test_boundaries_and_daily_repeat(self):
        value = validate_schedule(recipe())
        for minute, expected in (
            (0, 0),
            (359, 0),
            (360, 0.7),
            (1425, 1),
            (1439, 1),
            (1440, 0),
            (1800, 0.7),
        ):
            with self.subTest(minute=minute):
                self.assertEqual(scheduled_controls(value, minute)["uBoil"], expected)

    def test_invalid_commands_and_rows(self):
        for bad in (True, None, "0.5", float("nan"), float("inf"), -0.1, 1.01):
            value = recipe()
            value["entries"][0]["controls"]["uBoil"] = bad
            with self.subTest(value=bad), self.assertRaises(ValueError):
                validate_schedule(value)
        for times in (
            ("00:15",),
            ("00:00", "06:01"),
            ("00:00", "06:00", "06:00"),
            ("00:00", "24:00"),
            ("00:00", "08:00", "06:00"),
        ):
            value = recipe()
            value["entries"] = [
                {"time": time, "controls": dict.fromkeys(CONTROL_NAMES, 0)} for time in times
            ]
            with self.subTest(times=times), self.assertRaises(ValueError):
                validate_schedule(value)
        value = recipe()
        del value["entries"][0]["controls"]["uVent"]
        with self.assertRaises(ValueError):
            validate_schedule(value)

    def test_validation_copies_controls(self):
        original = recipe()
        validated = validate_schedule(original)
        original["entries"][0]["controls"]["uBoil"] = 1
        self.assertEqual(scheduled_controls(validated, 0)["uBoil"], 0)

    def test_application_rejects_invalid_schedule_without_touching_run(self):
        app = SimulatorApplication(FakeEngine(), requested_engine="glgym")
        app.step({"steps": 3})
        before = app.status()
        invalid = recipe()
        invalid["entries"][1]["time"] = "06:07"
        with self.assertRaises(ApiError):
            app.reset({"mode": "schedule", "schedule": invalid})
        self.assertEqual(app.status(), before)
        with self.assertRaises(ApiError):
            app.reset({"mode": "schedule"})
        app.reset({"mode": "schedule", "schedule": recipe(), "evaluationLimits": DEFAULT_LIMITS})
        self.assertEqual(app.status()["snapshot"]["mode"], "schedule")


class ClimateMetricTests(unittest.TestCase):
    def test_duration_weighting_inclusive_limits_and_union(self):
        metrics = ClimateMetrics(DEFAULT_LIMITS)
        for temperature, humidity in ((15, 50), (34, 85), (35, 86), (14, 60)):
            metrics.record(temperature, humidity, 15)
        value = metrics.snapshot()
        self.assertEqual(value["evaluatedMinutes"], 60)
        self.assertEqual(value["meanTemperature"], 24.5)
        self.assertEqual(value["meanHumidity"], 70.25)
        self.assertEqual(value["temperatureOutsideMinutes"], 30)
        self.assertEqual(value["humidityOutsideMinutes"], 15)
        self.assertEqual(value["eitherOutsideMinutes"], 30)

    def test_whole_run_exposure_survives_rolling_history_horizon(self):
        metrics = ClimateMetrics(DEFAULT_LIMITS)
        for _ in range(192):
            metrics.record(40, 70, 15)
        self.assertEqual(metrics.snapshot()["temperatureOutsideMinutes"], 2880)

    def test_invalid_limits_and_nonfinite_outputs(self):
        for key, value in (
            ("temperatureMin", True),
            ("humidityMax", 101),
            ("temperatureMax", float("nan")),
            ("temperatureMin", 34),
        ):
            limits = deepcopy(DEFAULT_LIMITS)
            limits[key] = value
            with self.assertRaises(ValueError):
                validate_limits(limits)
        with self.assertRaises(ValueError):
            ClimateMetrics(DEFAULT_LIMITS).record(float("inf"), 80, 15)
