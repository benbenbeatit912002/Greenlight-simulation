import math
import os
import unittest

from scripts.diagnose_davis import FORCING, STATES, classify, finite_or_none, named, source_clock


class DavisDiagnosticsTests(unittest.TestCase):
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
