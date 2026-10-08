from __future__ import annotations

import json
import unittest
from pathlib import Path

from backend.weather_upload import validate_weather_workbook
from examples.fetch_public_weather import PARAMETERS, SITES, convert

ROOT = Path(__file__).resolve().parents[1]


class PublicWeatherTests(unittest.TestCase):
    def test_published_examples_are_numeric_and_uploadable(self):
        for name in SITES:
            with self.subTest(site=name):
                raw = (ROOT / "templates" / f"weather-{name}.xlsx").read_bytes()
                result = validate_weather_workbook(raw, include_records=True)
                records = result["_records"]
                self.assertEqual(len(records), 1153)
                self.assertEqual(records[-1]["time"] - records[0]["time"], 4 * 86400)
                metadata = json.loads(
                    (ROOT / "templates" / f"weather-{name}.source.json").read_text(encoding="utf-8")
                )
                self.assertEqual(metadata["sourceYear"], 2023)
                self.assertEqual(metadata["sourceHeader"]["time_standard"], "UTC")
                self.assertRegex(metadata["rawSha256"], r"^[0-9a-f]{64}$")

    def test_conversion_rejects_missing_hours_and_changed_units(self):
        units = ("MJ/hr", "MJ/hr", "C", "%", "m/s", "%")
        payload = {
            "parameters": {key: {"units": unit} for key, unit in zip(PARAMETERS, units)},
            "header": {"time_standard": "UTC", "fill_value": -999},
            "properties": {"parameter": {key: {} for key in PARAMETERS}},
        }
        with self.assertRaisesRegex(ValueError, "Missing NASA source hour"):
            convert(payload, SITES["amsterdam-winter"])
        payload["parameters"]["T2M"]["units"] = "K"
        with self.assertRaisesRegex(ValueError, "units or time standard changed"):
            convert(payload, SITES["amsterdam-winter"])
