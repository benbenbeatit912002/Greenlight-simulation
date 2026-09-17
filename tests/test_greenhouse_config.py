import math
import unittest

from backend.greenhouse_config import (
    apply_initial_state,
    apply_parameters,
    validate_config,
)

DEFAULT = {"schemaVersion": 1, "overrides": {}}


def recipe(**overrides):
    return {"schemaVersion": 1, "overrides": overrides}


class ConfigurationContractTests(unittest.TestCase):
    def base(self):
        p = [0.0] * 208
        for i, v in {
            23: 1000,
            46: 144,
            47: 216.6,
            48: 5.7,
            49: 6.2,
            55: 52.2,
            56: 0.87,
            65: 0.13,
            66: 0.13,
            68: 0.57,
            69: 0.57,
            71: 1.05,
            73: 0.004,
            108: 18720,
            109: 720,
            111: 1.2,
            112: 6840,
            120: 600,
            122: 5.7,
            123: 0.5,
            144: 112781.95,
            172: 116,
        }.items():
            p[i] = v
        return p

    def test_default_copy_and_derived_geometry(self):
        base = self.base()
        self.assertEqual(apply_parameters(base, DEFAULT), base)
        p = apply_parameters(
            base,
            recipe(
                floorArea=288,
                coverArea=433.2,
                roofVentArea=104.4,
                mainHeight=6,
                totalHeight=7,
            ),
        )
        self.assertEqual((p[108], p[109]), (37440, 1440))
        for actual, expected in zip((p[112], p[120], p[122], p[123]), (7200, 1200, 6, 1)):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(base, self.base())

    def test_units_and_zero_capacities(self):
        p = apply_parameters(
            self.base(),
            recipe(boilerPower=0, co2Capacity=0, lampPower=0, roofThickness=8),
        )
        self.assertEqual((p[108], p[109], p[172]), (0, 0, 0))
        self.assertEqual(p[73], 0.008)

    def test_invalid_structure_and_numbers(self):
        for bad in (
            None,
            {},
            [],
            {"schemaVersion": True, "overrides": {}},
            recipe(typo=5),
            recipe(floorArea=True),
            recipe(floorArea="10"),
            recipe(floorArea=float("nan")),
            recipe(floorArea=float("inf")),
            recipe(floorArea=10**1000),
            recipe(initialFruit=-1),
        ):
            with self.subTest(bad=repr(bad)[:70]), self.assertRaises(ValueError):
                validate_config(bad)

    def test_invalid_dependencies(self):
        for config in (
            recipe(mainHeight=6.2),
            recipe(floorArea=300),
            recipe(roofVentArea=200),
            recipe(initialLeaf=113),
            recipe(roofParTransmission=0.9),
        ):
            with self.subTest(config=config), self.assertRaises(ValueError):
                apply_parameters(self.base(), config)

    def test_initial_air_conversion_and_unexposed_states(self):
        def sat(t):
            return 610.78 * math.exp(17.2694 * t / (t + 238.3))

        def to_ppm(t, d):
            return 1e6 * 8.3144598 * (t + 273.15) * d / (101325 * 0.04401)

        def to_dens(t, c):
            return c * 1e-6 * 101325 * 0.04401 / (8.3144598 * (t + 273.15))

        x = [1.0] * 28
        x[2] = 16.5
        x[15] = 0.9 * sat(16.5)
        x[0] = to_dens(16.5, 500) * 1e6
        kwargs = {
            "sat_vp": sat,
            "co2_density_to_ppm": to_ppm,
            "co2_ppm_to_density": to_dens,
        }
        self.assertEqual(apply_initial_state(x, DEFAULT, **kwargs), x)
        y = apply_initial_state(
            x,
            recipe(initialAirTemp=22, initialLeaf=90, initialStem=250, initialFruit=60),
            **kwargs,
        )
        self.assertAlmostEqual(y[15] / sat(22) * 100, 90)
        self.assertAlmostEqual(to_ppm(22, y[0] * 1e-6), 500)
        self.assertEqual(y[23:26], [90000, 250000, 60000])
        for index in set(range(28)) - {0, 2, 15, 23, 24, 25}:
            self.assertEqual(x[index], y[index])


if __name__ == "__main__":
    unittest.main()
