import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

from weather_fixtures import workbook_bytes

from backend.server import ApiError, SimulatorApplication, build_parser
from backend.weather_source import require_single_year_coverage, single_year_loader
from backend.weather_upload import (
    AMSTERDAM_COLUMNS,
    WeatherValidationError,
    validate_weather_workbook,
)


class AmsterdamContractTests(unittest.TestCase):
    def rows(self):
        return [[time, 0, 2, 10, 4, 0, 400, time / 86400, 80] for time in (0, 300, 600)]

    def validate(self, rows, headers=AMSTERDAM_COLUMNS):
        return validate_weather_workbook(workbook_bytes(rows, headers, dimension="A1:A1"))

    def test_exact_schema_and_source_time_no_inferred_timezone(self):
        result = self.validate(self.rows())
        self.assertEqual(result["columns"], list(AMSTERDAM_COLUMNS))
        self.assertEqual(result["intervalMinutes"], 5)
        self.assertEqual(result["start"], "0 s")
        self.assertEqual(result["timezone"], "not specified in source")
        self.assertFalse(result["simulationReady"])
        self.assertFalse(result["stored"])

    def test_reordered_headers_rejected(self):
        with self.assertRaises(WeatherValidationError):
            self.validate(self.rows(), tuple(reversed(AMSTERDAM_COLUMNS)))

    def test_gaps_duplicates_text_and_unknown_missing_rejected(self):
        for column, value in [
            (0, 0),
            (0, 900),
            (0, "300"),
            (5, None),
            (8, 101),
            (4, True),
            (1, ("1+1",)),
        ]:
            with self.subTest(column=column, value=value):
                rows = self.rows()
                rows[1][column] = value
                with self.assertRaises(WeatherValidationError):
                    self.validate(rows)

    def test_blank_middle_row_rejected(self):
        with self.assertRaises(WeatherValidationError):
            self.validate([self.rows()[0], [], self.rows()[1]])

    def test_later_window_accepted_without_year_assignment(self):
        rows = self.rows()
        for row in rows:
            row[0] += 59 * 86400
        result = self.validate(rows)
        self.assertEqual(result["start"], f"{59 * 86400} s")


class ScientificOnlyTests(unittest.TestCase):
    def test_default_cli_requires_full_model(self):
        self.assertEqual(build_parser().parse_args([]).engine, "glgym")

    def test_no_engine_has_no_snapshot_and_no_approximation(self):
        app = SimulatorApplication(None, requested_engine="auto")
        status = app.status()
        self.assertEqual(status["engine"]["active"], "unavailable")
        self.assertIsNone(status["snapshot"])
        self.assertFalse(status["engine"]["scientific"])

    def test_failed_step_invalidates_revision_until_explicit_reset(self):
        engine = Mock()
        engine.step.side_effect = RuntimeError("solver failed after partial progress")
        engine.reset.return_value = {"modelStep": 0}
        app = SimulatorApplication(engine, requested_engine="glgym")
        with self.assertRaises(ApiError):
            app.step({"steps": 4, "expectedRevision": 0})
        self.assertEqual(app.revision, 1)
        with self.assertRaises(ApiError):
            app.status()
        with self.assertRaises(ApiError):
            app.step({"steps": 1, "expectedRevision": 1})
        self.assertEqual(engine.step.call_count, 1)
        app.reset({"expectedRevision": 1})
        self.assertIsNone(app.model_error)

    def test_ui_never_constructs_browser_model(self):
        root = Path(__file__).resolve().parents[1]
        app = (root / "frontend/app.js").read_text(encoding="utf-8")
        html = (root / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("GreenhouseModel", app)
        self.assertNotIn("switchToBrowserFallback", app)
        self.assertNotIn('src="simulator-engine.js"', html)
        self.assertIn("model-unavailable", html)


class SingleYearSafetyTests(unittest.TestCase):
    def test_cross_year_rejected_before_upstream_loader(self):
        # Synthetic time column, not a research file. No filesystem writes.
        csv = "time\n" + "\n".join(str(i * 21600) for i in range(1460))
        with patch.object(Path, "open", return_value=StringIO(csv)):
            with self.assertRaises(ValueError):
                require_single_year_coverage(
                    Path("unused.csv"), start_day=305, n_days=60, pred_horizon=0.5
                )
        with patch.object(Path, "open", return_value=StringIO(csv)):
            require_single_year_coverage(
                Path("unused.csv"), start_day=295, n_days=60, pred_horizon=0.5
            )

    def test_unapproved_file_is_never_opened(self):
        upstream = Mock()
        loader = single_year_loader(upstream)
        with patch.object(Path, "open", side_effect=AssertionError("must not read")):
            with self.assertRaises(ValueError):
                loader(location="Amsterdam", growth_year=2011)
        upstream.assert_not_called()

    def test_nonzero_time_origin_rejected(self):
        with patch.object(Path, "open", return_value=StringIO("time\n300\n600\n")):
            with self.assertRaises(ValueError):
                require_single_year_coverage(
                    Path("unused.csv"), start_day=0, n_days=1, pred_horizon=0
                )
