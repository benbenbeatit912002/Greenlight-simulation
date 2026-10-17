from __future__ import annotations

import copy
import math
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from backend.weather_archive import PARAMETER_UNITS, convert_hourly, greenlight_window, source_url
from examples.collect_weather import DATA, ROOT, fetch_raw, json_bytes, local_path, save_new


def payload(year):
    start, end = datetime(year, 1, 1), datetime(year + 1, 1, 1)
    keys = [
        (start + timedelta(hours=i)).strftime("%Y%m%d%H")
        for i in range(int((end - start).total_seconds() / 3600))
    ]
    values = (0.36, 1.08, 12.0, 75.0, 2.0, 60.0)
    return {
        "header": {"time_standard": "UTC", "fill_value": -999},
        "parameters": {name: {"units": units} for name, units in PARAMETER_UNITS.items()},
        "properties": {
            "parameter": {
                name: dict.fromkeys(keys, value) for name, value in zip(PARAMETER_UNITS, values)
            }
        },
    }


class WeatherArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = payload(2023)
        cls.rows = convert_hourly(cls.source, 2023)

    def test_complete_year_and_units(self):
        self.assertEqual(len(self.rows), 8760)
        self.assertAlmostEqual(self.rows[0]["shortwave_w_m2"], 100)
        self.assertAlmostEqual(self.rows[0]["longwave_w_m2"], 300)
        self.assertAlmostEqual(
            self.rows[0]["sky_temperature_c"], (300 / 5.670374419e-8) ** 0.25 - 273.15
        )
        self.assertEqual(len(convert_hourly(payload(2024), 2024)), 8784)

    def test_reject_missing_units_time_and_nonfinite(self):
        for change in ("missing", "units", "clock", "fill", "nan", "range"):
            with self.subTest(change=change):
                p = copy.deepcopy(self.source)
                if change == "missing":
                    del p["properties"]["parameter"]["T2M"]["2023010100"]
                elif change == "units":
                    p["parameters"]["T2M"]["units"] = "K"
                elif change == "clock":
                    p["header"]["time_standard"] = "LST"
                else:
                    p["properties"]["parameter"]["RH2M"]["2023010100"] = {
                        "fill": -999,
                        "nan": math.nan,
                        "range": 101,
                    }[change]
                with self.assertRaises(ValueError):
                    convert_hourly(p, 2023)

    def test_window_holds_values_without_changing_source(self):
        rows = greenlight_window(self.rows, datetime(2023, 1, 15))
        self.assertEqual(len(rows), 1153)
        self.assertEqual(rows[-1]["time"] - rows[0]["time"], 96 * 3600)
        self.assertTrue(all(b["time"] - a["time"] == 300 for a, b in zip(rows, rows[1:])))
        self.assertEqual(rows[0]["CO2 concentration"], 400)
        self.assertNotIn("CO2 concentration", self.rows[0])
        self.assertEqual(len(self.rows), 8760)

    def test_window_rejects_missing_hours_duplicates_and_cross_year(self):
        with self.assertRaisesRegex(ValueError, "Missing source hour"):
            greenlight_window(self.rows[1:], datetime(2023, 1, 1))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            greenlight_window(self.rows + [self.rows[0]], datetime(2023, 1, 1))
        with self.assertRaisesRegex(ValueError, "one source year"):
            greenlight_window(self.rows, datetime(2023, 12, 30))

    def test_fixed_offset_uses_correct_source_hour_without_dst(self):
        rows = copy.deepcopy(self.rows)
        rows[24]["air_temperature_c"] = 31.25
        shifted = greenlight_window(rows, datetime(2023, 1, 2, 8), utc_offset_hours=8)
        self.assertEqual(shifted[0]["air temperature"], 31.25)
        self.assertEqual(shifted[0]["time"], 32 * 3600)
        self.assertEqual(shifted[0]["day number"], 2)
        with self.assertRaisesRegex(ValueError, "UTC offset"):
            greenlight_window(rows, datetime(2023, 1, 2), utc_offset_hours=24)

    def test_paths_and_source_query_are_bounded(self):
        with self.assertRaises(ValueError):
            local_path(DATA / ".." / "outside.json")
        url = source_url({"latitude": 25, "longitude": 121}, 2024)
        self.assertIn("time-standard=UTC", url)
        self.assertIn("end=20241231", url)
        for site, year in (
            ({"latitude": 91, "longitude": 0}, 2023),
            ({"latitude": 0, "longitude": 0}, 2000),
        ):
            with self.assertRaises(ValueError):
                source_url(site, year)

    def test_existing_download_is_never_overwritten(self):
        runtime = ROOT / ".runtime"
        runtime.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=runtime) as temp:
            root = Path(temp)
            with patch("examples.collect_weather.DATA", root):
                target = root / "source.json"
                save_new(target, b"original")
                save_new(target, b"original")
                with self.assertRaises(FileExistsError):
                    save_new(target, b"replacement")
                self.assertEqual(target.read_bytes(), b"original")

    def test_cached_response_requires_matching_query_and_hash(self):
        import hashlib

        runtime = ROOT / ".runtime"
        runtime.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=runtime) as temp:
            root = Path(temp)
            raw = b'{"fixture": true}'
            with patch("examples.collect_weather.DATA", root):
                save_new(root / "source.json", raw)
                save_new(
                    root / "request.json",
                    json_bytes(
                        {
                            "url": "https://example.invalid/a",
                            "sha256": hashlib.sha256(raw).hexdigest(),
                        }
                    ),
                )
                with patch("examples.collect_weather.urlopen") as network:
                    self.assertEqual(fetch_raw(root, "https://example.invalid/a")[0], raw)
                    with self.assertRaisesRegex(ValueError, "does not match"):
                        fetch_raw(root, "https://example.invalid/b")
                    network.assert_not_called()


if __name__ == "__main__":
    unittest.main()
