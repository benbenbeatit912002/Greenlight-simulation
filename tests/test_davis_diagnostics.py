import math
import os
import unittest

from scripts.diagnose_davis import (
    FORCING,
    STATES,
    attempt_messages,
    case_inputs,
    classify,
    finite_or_none,
    matched_window,
    named,
    source_clock,
)


class DavisDiagnosticsTests(unittest.TestCase):
    def test_only_failed_production_attempt_contributes_solver_warnings(self):
        case = {"year": 2023, "completedSteps": 44}
        stderr = (
            "old warning\nDAVIS_NATIVE_2023_44_BEGIN\noriginal warning\n"
            "DAVIS_NATIVE_2023_44_END\nretry warning\n"
        )
        self.assertEqual(attempt_messages(case, stderr), "original warning\n")
        self.assertEqual(attempt_messages({**case, "completedSteps": 45}, stderr), "")
        self.assertEqual(attempt_messages(case, stderr.split("_END")[0]), "")

    def test_davis_reads_only_the_named_collection_after_path_checks(self):
        from unittest.mock import patch

        with (
            patch("scripts.diagnose_davis.project_destination") as checked,
            patch("scripts.diagnose_davis.load_year") as loader,
        ):
            case_inputs(2024, "fresh-collection")
            loader.assert_called_once_with("davis-us", 2024, collection="fresh-collection")
            self.assertEqual(len(checked.call_args_list), 3)
            self.assertTrue(
                all("fresh-collection" in str(c.args[0]) for c in checked.call_args_list)
            )
        with (
            patch("scripts.diagnose_davis.project_destination", side_effect=ValueError("Linked")),
            patch("scripts.diagnose_davis.load_year") as loader,
            self.assertRaisesRegex(ValueError, "Linked"),
        ):
            case_inputs(2024, "fresh-collection")
        loader.assert_not_called()

    def test_full_window_requires_same_inputs_and_three_complete_days(self):
        case = {
            "model": "model",
            "initial": "initial",
            "parameters": "params",
            "configuration": "config",
            "weather": "weather",
            "sourceSha256": "raw",
            "window": {"totalSteps": 288},
        }
        initial = {
            "modelVersion": "model",
            "initialStateFingerprint": "initial",
            "parameterFingerprint": "params",
            "configurationFingerprint": "config",
            "weatherFingerprint": "weather",
            "runWindow": {"totalSteps": 288},
        }
        self.assertTrue(matched_window(case, initial, "raw"))
        self.assertFalse(matched_window(case, initial, "other raw data"))
        for key in initial:
            wrong = {"totalSteps": 287} if key == "runWindow" else "different"
            self.assertFalse(matched_window(case, {**initial, key: wrong}, "raw"))

    def test_inconclusive_contrasts_are_not_called_reproduced(self):
        evidence = {
            "originalEndpointFinite": False,
            "stableEndpointFinite": True,
            "originalSolverMessage": "CV_CONV_FAILURE",
        }
        case = {
            "year": 2024,
            "completedSteps": 244,
            "status": "failed",
            "matchedStepExperiment": evidence,
        }
        message = "NaN detected for output jac_ode_x, at nonzero index 49 (row 5, col 5)."
        self.assertEqual(
            classify(case, message)["verdict"], "matched numerical contrast reproduced"
        )
        self.assertEqual(classify(case, "")["verdict"], "inconclusive")
        for change in (
            {"originalEndpointFinite": True},
            {"stableEndpointFinite": False},
            {"originalSolverMessage": "unrelated"},
        ):
            self.assertEqual(
                classify({**case, "matchedStepExperiment": {**evidence, **change}}, message)[
                    "verdict"
                ],
                "inconclusive",
            )

    def test_state_order_and_clock_match_pinned_cases(self):
        self.assertEqual((len(STATES), STATES[5], STATES[16]), (28, "tCovIn", "vpTop"))
        self.assertEqual(len(FORCING), 10)
        self.assertEqual(
            source_clock(2023, 195 * 86400 + 11 * 3600, -8), "2023-07-15T11:00:00-08:00"
        )
        self.assertIsNone(finite_or_none(math.nan))
        with self.assertRaises(ValueError):
            named(("one", "two"), [0])

    @unittest.skipUnless(os.getenv("RUN_GREENLIGHT_INTEGRATION") == "1", "Opt-in Jacobian probe")
    def test_hot_cover_jacobian_and_equivalent_rates(self):
        from examples.weather_runs import new_adapter
        from scripts.diagnose_davis import evaluate, probe_graphs

        engine = new_adapter()
        try:
            probe, _ = probe_graphs()
            x = engine.core.x.copy()
            p, d, u = engine.core.p, engine.core.weather_data[0], engine.core.u
            for cover_c, at_risk in ((20, False), (48, True)):
                x[5], x[16] = cover_c, 2500
                out = evaluate(probe, x, u, d, p)
                self.assertEqual(out["originalJac55Finite"], not at_risk)
                self.assertTrue(out["stableJac55Finite"])
                self.assertLess(out["rhsMaxAbsDifference"], 1e-12)
                self.assertEqual(out["exponent"] > out["logFloat64Max"], at_risk)
        finally:
            engine.close()
