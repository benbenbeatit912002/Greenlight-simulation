from __future__ import annotations

import math
import os
import unittest
from typing import Any

from backend.greenlight_adapter import GreenLightGymAdapter


def assert_finite_numbers(test: unittest.TestCase, value: Any, path: str = "snapshot") -> None:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, (int, float)):
        test.assertTrue(math.isfinite(float(value)), f"non-finite value at {path}: {value}")
        return
    if isinstance(value, dict):
        for key, child in value.items():
            assert_finite_numbers(test, child, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            assert_finite_numbers(test, child, f"{path}[{index}]")


@unittest.skipUnless(
    os.environ.get("RUN_GREENLIGHT_INTEGRATION") == "1",
    "set RUN_GREENLIGHT_INTEGRATION=1 to construct the CasADi model",
)
class GreenLightIntegrationTests(unittest.TestCase):
    def test_real_model_reset_and_absolute_control_step(self) -> None:
        adapter = GreenLightGymAdapter()
        try:
            reset_snapshot = adapter.reset(
                {
                    "seed": 42,
                    "scenario": "spring",
                    "mode": "manual",
                    "targets": {"dayTemp": 21.5, "nightTemp": 17.5, "co2": 900, "maxRh": 82},
                }
            )
            self.assertEqual(reset_snapshot["engine"], "greenlight-gym2")
            self.assertEqual(reset_snapshot["modelStep"], 0)
            self.assertAlmostEqual(reset_snapshot["crop"]["fruitDryMass"], 55.338, places=2)

            controls = {
                "uBoil": 0.35,
                "uCO2": 0.15,
                "uThScr": 0.4,
                "uVent": 0.05,
                "uLamp": 0.25,
                "uBlScr": 0.0,
            }
            stepped = adapter.step(
                {"steps": 1, "mode": "manual", "controls": controls}
            )
            self.assertEqual(stepped["modelStep"], 1)
            for name, expected in controls.items():
                self.assertAlmostEqual(stepped["controls"][name], expected, places=4)
            self.assertEqual(len(stepped["history"]), 2)
            assert_finite_numbers(self, stepped)
        finally:
            adapter.close()


if __name__ == "__main__":
    unittest.main()
