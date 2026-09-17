import unittest

from backend.run_window import coverage, source_datetime, validate_window


class RunWindowTests(unittest.TestCase):
    def setUp(self):
        self.bounds = coverage(0, 129600)
        self.request = {
            "sourceYear": 2010,
            "timeConvention": "source-local-standard",
            "startSeconds": 33300,
            "endSeconds": 36000,
        }

    def test_non_midnight_steps_and_calendar(self):
        window = validate_window(self.request, self.bounds)
        self.assertEqual(window["totalSteps"], 3)
        self.assertEqual(window["startDateTime"], "2010-01-01T09:15")
        self.assertEqual(window["endDateTime"], "2010-01-01T10:00")
        self.assertEqual(window["warmupSeconds"], 0)

    def test_one_step_and_exact_last_endpoint(self):
        window = validate_window(
            {**self.request, "startSeconds": 85500, "endSeconds": 86400}, self.bounds
        )
        self.assertEqual(window["totalSteps"], 1)
        self.assertEqual(
            window["endSeconds"] + window["lookaheadSeconds"],
            self.bounds["sourceEndSeconds"],
        )

    def test_initialization_context_and_daily_radiation_coverage(self):
        self.assertEqual(coverage(300, 3 * 86400)["earliestStartSeconds"], 86400)
        self.assertEqual(coverage(0, 40 * 3600)["latestEndSeconds"], 86400)

    def test_invalid_windows(self):
        for changes in (
            {"startSeconds": True},
            {"endSeconds": 36001},
            {"endSeconds": 33300},
            {"startSeconds": -900},
            {"endSeconds": 87300},
            {"sourceYear": 2010.5},
            {"sourceYear": 0},
            {"timeConvention": "Europe/Amsterdam"},
            {"extra": 1},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_window({**self.request, **changes}, self.bounds)
        with self.assertRaises(ValueError):
            validate_window(None, self.bounds)

    def test_leap_day_and_year_end(self):
        self.assertEqual(source_datetime(2024, 59 * 86400), "2024-02-29T00:00")
        self.assertEqual(source_datetime(2023, 59 * 86400), "2023-03-01T00:00")
        bounds = coverage(364 * 86400, 366 * 86400)
        request = {
            **self.request,
            "sourceYear": 2024,
            "startSeconds": 364 * 86400,
            "endSeconds": 365 * 86400,
        }
        self.assertEqual(validate_window(request, bounds)["totalSteps"], 96)
        with self.assertRaises(ValueError):
            validate_window({**request, "sourceYear": 2023}, bounds)
