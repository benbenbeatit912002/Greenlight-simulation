from __future__ import annotations

import http.client
import json
import math
import os
import threading
import unittest
from typing import Any
from unittest.mock import patch

from backend.greenhouse_config import FIELDS
from backend.greenlight_adapter import GreenLightGymAdapter, _array_fingerprint
from backend.server import ApiError, SimulatorApplication, create_server
from backend.weather_upload import XLSX_MIME
from tests.weather_fixtures import workbook_bytes

DEFAULT_WINDOW = {
    "sourceYear": 2010,
    "timeConvention": "source-local-standard",
    "startSeconds": 0,
    "endSeconds": 86400,
}


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
                    "targets": {
                        "dayTemp": 21.5,
                        "nightTemp": 17.5,
                        "co2": 900,
                        "maxRh": 82,
                    },
                }
            )
            self.assertEqual(reset_snapshot["engine"], "greenlight-gym2")
            metadata = adapter.metadata()
            self.assertRegex(
                metadata["sourceFingerprint"],
                r"^[0-9a-f]{64}$",
            )
            self.assertRegex(
                metadata["parameterFingerprint"],
                r"^[0-9a-f]{64}$",
            )
            self.assertRegex(
                metadata["weatherFingerprint"],
                r"^[0-9a-f]{64}$",
            )
            if metadata["gitRevision"] is not None:
                self.assertRegex(metadata["gitRevision"], r"^[0-9a-f]{40}$")
                self.assertIn(metadata["gitRevision"], reset_snapshot["modelVersion"])
            else:
                self.assertIn(
                    metadata["sourceFingerprint"],
                    reset_snapshot["modelVersion"],
                )
            self.assertNotIn("unversioned", reset_snapshot["modelVersion"])
            self.assertNotIn("local-source", reset_snapshot["modelVersion"])
            self.assertEqual(
                reset_snapshot["weatherFingerprint"],
                metadata["weatherFingerprint"],
            )
            self.assertEqual(
                reset_snapshot["costModelId"],
                "greenlight-gym2-variable-costs",
            )
            self.assertFalse(reset_snapshot["economics"]["liveTariff"])
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
            stepped = adapter.step({"steps": 1, "mode": "manual", "controls": controls})
            self.assertEqual(stepped["modelStep"], 1)
            self.assertEqual(stepped["runId"], reset_snapshot["runId"])
            self.assertEqual(adapter.snapshot()["runId"], stepped["runId"])
            for name, expected in controls.items():
                self.assertAlmostEqual(stepped["controls"][name], expected, places=4)
            self.assertEqual(len(stepped["history"]), 2)
            assert_finite_numbers(self, stepped)
            # Compare adapter outputs with the original scientific auxiliary
            # function, including a daytime forcing row and different screens.
            import casadi as ca
            import numpy as np
            from gl_gym.models.GreenLight.aux_states import update

            def assert_aux(snapshot):
                index = max(0, adapter.core.timestep - 1)
                aux = np.asarray(
                    ca.DM(
                        update(
                            adapter.core.x,
                            adapter.core.u,
                            adapter.core.weather_data[index],
                            adapter.core.p,
                        )
                    ),
                    dtype=float,
                ).reshape(-1)
                self.assertEqual(
                    snapshot["indoor"]["insideRadiation"],
                    round(float(aux[42] + aux[43]), 0),
                )
                self.assertEqual(snapshot["indoor"]["canopyAbsorbedPar"], round(float(aux[191]), 1))
                self.assertEqual(snapshot["crop"]["leafAreaIndex"], round(float(aux[31]), 2))
                self.assertEqual(snapshot["outputDefinitions"]["forcingIndex"], index)

            assert_aux(stepped)
            daytime = adapter.step({"steps": 48, "mode": "auto"})
            assert_aux(daytime)
            assert_finite_numbers(self, daytime)
            self.assertGreater(daytime["indoor"]["insideRadiation"], 0)
            for scenario in ("cloudy", "summer", "winter"):
                previous_run = adapter.snapshot()["runId"]
                snapshot = adapter.reset({"scenario": scenario})
                self.assertNotEqual(snapshot["runId"], previous_run)
                assert_aux(snapshot)
                assert_finite_numbers(self, snapshot)
        finally:
            adapter.close()

    def test_uploaded_amsterdam_weather_runs_in_memory(self) -> None:
        adapter = GreenLightGymAdapter()
        try:
            records = [
                {
                    "time": index * 300,
                    "global radiation": 300 if 24 <= index % 288 <= 72 else 0,
                    "wind speed": 2.0,
                    "air temperature": 12.0,
                    "sky temperature": 5.0,
                    "??": 0.0,
                    "CO2 concentration": 520.0,
                    "day number": index * 300 / 86400,
                    "RH": 75.0,
                }
                for index in range(433)
            ]
            prepared = adapter.prepare_uploaded_weather(records)
            self.assertEqual(prepared["seasonLengthDays"], 1)
            self.assertEqual(prepared["modelRowCount"], 145)
            self.assertGreater(prepared["weather"][24, 0], prepared["weather"][0, 0])
            self.assertGreater(prepared["weather"][0, 3], 0)
            snapshot = adapter.reset(
                {
                    "scenario": "uploaded",
                    "_prepared_weather": prepared,
                    "_weather_id": "synthetic-weather-2026",
                    "_weather_label": "Synthetic uploaded weather",
                    "runWindow": DEFAULT_WINDOW,
                }
            )
            self.assertEqual(snapshot["scenario"], "uploaded")
            self.assertEqual(snapshot["weatherId"], "synthetic-weather-2026")
            self.assertEqual(adapter.metadata()["weatherSource"], "uploaded-in-memory")
            stepped = adapter.step({"steps": 1, "mode": "auto"})
            self.assertEqual(stepped["runId"], snapshot["runId"])
            assert_finite_numbers(self, stepped)
            restored = adapter.reset({"scenario": "spring"})
            self.assertEqual(restored["scenario"], "spring")
            self.assertIsNone(restored["weatherId"])
        finally:
            adapter.close()

    def test_uploaded_weather_http_flow_uses_full_model(self) -> None:
        adapter = GreenLightGymAdapter()
        server = create_server(port=0, requested_engine="glgym", engine=adapter)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            headers = (
                "time",
                "global radiation",
                "wind speed",
                "air temperature",
                "sky temperature",
                "??",
                "CO2 concentration",
                "day number",
                "RH",
            )
            rows = [
                [
                    index * 300,
                    300 if 24 <= index % 288 <= 72 else 0,
                    2,
                    12,
                    5,
                    0,
                    520,
                    index * 300 / 86400,
                    75,
                ]
                for index in range(433)
            ]
            upload = workbook_bytes(rows, headers=headers)
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=20)
            connection.request(
                "POST",
                "/api/weather/preview",
                body=upload,
                headers={"Content-Type": XLSX_MIME, "X-GreenLight-Upload": "1"},
            )
            response = connection.getresponse()
            body = json.loads(response.read())
            self.assertEqual(response.status, 200)
            self.assertTrue(body["weather"]["conversionReady"])
            self.assertFalse(body["weather"]["modelReady"])
            weather_id = body["weather"]["weatherId"]
            connection.request(
                "POST",
                "/api/reset",
                body=json.dumps(
                    {
                        "scenario": "uploaded",
                        "weatherId": weather_id,
                        "runWindow": DEFAULT_WINDOW,
                        "expectedRevision": 0,
                    }
                ).encode(),
                headers={"Content-Type": "application/json"},
            )
            reset_response = connection.getresponse()
            reset_body = json.loads(reset_response.read())
            self.assertEqual(reset_response.status, 200)
            self.assertTrue(reset_body["snapshot"]["modelReady"])
            self.assertEqual(reset_body["snapshot"]["scenario"], "uploaded")
            connection.request(
                "POST",
                "/api/step",
                body=json.dumps({"steps": 1, "mode": "auto", "expectedRevision": 1}).encode(),
                headers={"Content-Type": "application/json"},
            )
            step_response = connection.getresponse()
            step_body = json.loads(step_response.read())
            self.assertEqual(step_response.status, 200)
            assert_finite_numbers(self, step_body["snapshot"])
            connection.close()
        finally:
            server.shutdown()
            worker.join(2)
            server.application.close()
            server.server_close()

    def test_greenhouse_settings_map_to_effective_model_and_defaults_reproduce(self):
        adapter = GreenLightGymAdapter()
        empty = {"schemaVersion": 1, "overrides": {}}
        try:
            baseline = adapter.reset({"scenario": "spring", "greenhouseConfig": empty})
            initial_x = adapter.core.x.copy()
            base_p = adapter.core.p.copy()
            adapter.step({"steps": 3, "mode": "auto"})
            end_x = adapter.core.x.copy()
            repeated = adapter.reset({"scenario": "spring", "greenhouseConfig": empty})
            self.assertTrue(adapter._np.array_equal(adapter.core.p, base_p))
            self.assertTrue(adapter._np.array_equal(adapter.core.x, initial_x))
            self.assertEqual(
                baseline["configurationFingerprint"],
                repeated["configurationFingerprint"],
            )
            adapter.step({"steps": 3, "mode": "auto"})
            self.assertTrue(adapter._np.allclose(adapter.core.x, end_x, rtol=1e-10, atol=1e-8))
            changes = {
                "floorArea": 288,
                "coverArea": 433.2,
                "mainHeight": 6,
                "totalHeight": 7,
                "roofVentArea": 104.4,
                "ventHeight": 1,
                "boilerPower": 150,
                "co2Capacity": 6,
                "lampPower": 100,
                "roofParTransmission": 0.6,
                "roofNirTransmission": 0.55,
                "roofThickness": 5,
                "roofConductivity": 1.2,
                "initialAirTemp": 22,
                "initialRh": 70,
                "initialCo2": 800,
                "initialLeaf": 90,
                "initialStem": 250,
                "initialFruit": 60,
                "initialCanopyTemp": 23,
                "initialCanopy24h": 21,
                "initialTempSum": 2000,
            }
            result = adapter.reset(
                {
                    "scenario": "spring",
                    "greenhouseConfig": {"schemaVersion": 1, "overrides": changes},
                }
            )
            for row in FIELDS:
                key, index = row[0], row[7]
                with self.subTest(field=key):
                    self.assertAlmostEqual(
                        result["greenhouse"]["effective"][key], changes[key], places=5
                    )
                    if index is not None:
                        scale = (
                            288
                            if key in ("boilerPower", "co2Capacity")
                            else 0.001
                            if key == "roofThickness"
                            else 1
                        )
                        self.assertAlmostEqual(adapter.core.p[index], changes[key] * scale)
            self.assertTrue(
                adapter._np.array_equal(adapter.core.base_p, base_p),
                "upstream defaults unchanged",
            )
            self.assertEqual(adapter.core.p[112], 6 * adapter.core.p[111] * adapter.core.p[23])
            self.assertEqual(adapter.core.p[120], adapter.core.p[111] * adapter.core.p[23])
            self.assertEqual(
                result["parameterFingerprint"],
                _array_fingerprint(adapter._np, adapter.core.p),
            )
            self.assertEqual(
                result["initialStateFingerprint"],
                _array_fingerprint(adapter._np, adapter.core.x),
            )
            self.assertNotEqual(
                result["configurationFingerprint"], baseline["configurationFingerprint"]
            )
            self.assertAlmostEqual(result["indoor"]["airTemp"], 22)
            self.assertAlmostEqual(result["indoor"]["rh"], 70)
            self.assertEqual(result["indoor"]["co2"], 800)
            self.assertEqual(result["crop"]["fruitDryMass"], 60)
            final = adapter.step({"steps": 3, "mode": "auto"})
            assert_finite_numbers(self, final)
            self.assertEqual(final["configurationFingerprint"], result["configurationFingerprint"])
            self.assertEqual(final["greenhouse"], result["greenhouse"])
            before = adapter.snapshot()
            with self.assertRaises(ValueError):
                adapter.reset(
                    {
                        "greenhouseConfig": {
                            "schemaVersion": 1,
                            "overrides": {"mainHeight": 10},
                        }
                    }
                )
            self.assertEqual(adapter.snapshot(), before)
            default = adapter.reset({"scenario": "spring", "greenhouseConfig": empty})
            self.assertEqual(
                default["configurationFingerprint"],
                baseline["configurationFingerprint"],
            )
        finally:
            adapter.close()

    def test_geometry_scaling_and_zero_capacity_resource_accounting(self):
        adapter = GreenLightGymAdapter()

        def run(overrides):
            adapter.reset(
                {
                    "scenario": "spring",
                    "greenhouseConfig": {"schemaVersion": 1, "overrides": overrides},
                }
            )
            return adapter.step(
                {
                    "steps": 2,
                    "mode": "manual",
                    "controls": {
                        "uBoil": 0.5,
                        "uCO2": 0.3,
                        "uThScr": 0.1,
                        "uVent": 0.2,
                        "uLamp": 0.5,
                        "uBlScr": 0,
                    },
                }
            )

        try:
            original = run({})
            p = adapter.core.base_p
            scaled = run(
                {
                    "floorArea": float(p[46] * 2),
                    "coverArea": float(p[47] * 2),
                    "roofVentArea": float(p[55] * 2),
                }
            )
            self.assertEqual(
                scaled["resources"],
                original["resources"],
                "per-area quantities invariant under proportional area scaling",
            )
            self.assertEqual(scaled["indoor"], original["indoor"])
            for key in original["wholeGreenhouseResources"]:
                self.assertAlmostEqual(
                    scaled["wholeGreenhouseResources"][key],
                    original["wholeGreenhouseResources"][key] * 2,
                    delta=0.002,
                )
            zero = run({"boilerPower": 0, "lampPower": 0, "co2Capacity": 0, "roofVentArea": 0})
            self.assertEqual(
                zero["resources"],
                {"heatKwh": 0, "lampKwh": 0, "co2Kg": 0, "costEur": 0},
            )
            self.assertEqual(adapter.core.reward_fn.min_profit, 0)
            assert_finite_numbers(self, zero)
        finally:
            adapter.close()

    def test_later_year_partial_first_day_preserves_calendar_and_soil_season(self):
        adapter = GreenLightGymAdapter()
        try:
            origin = 58 * 86400 + 300
            records = [
                {
                    "time": origin + index * 300,
                    "global radiation": 200,
                    "wind speed": 2,
                    "air temperature": 12,
                    "sky temperature": 5,
                    "??": 0,
                    "CO2 concentration": 450,
                    "day number": 0,
                    "RH": 75,
                }
                for index in range(577)
            ]
            prepared = adapter.prepare_uploaded_weather(records)
            self.assertEqual(prepared["coverage"]["earliestStartSeconds"], 59 * 86400)
            start = 59 * 86400 + 33300
            window = {
                **DEFAULT_WINDOW,
                "sourceYear": 2024,
                "startSeconds": start,
                "endSeconds": start + 2700,
            }
            initial = adapter.reset(
                {
                    "scenario": "uploaded",
                    "_prepared_weather": prepared,
                    "runWindow": window,
                }
            )
            self.assertEqual(initial["runProgress"]["currentDateTime"], "2024-02-29T09:15")
            self.assertAlmostEqual(adapter.core.day_of_year, 1 + start / 86400)
            self.assertAlmostEqual(
                adapter.core.weather_data[0, 6], float(adapter._soil_temperature(start))
            )
            self.assertNotAlmostEqual(
                adapter.core.weather_data[0, 6], float(adapter._soil_temperature(0))
            )
            finished = adapter.step({"steps": 192, "mode": "auto"})
            self.assertEqual(finished["runProgress"]["currentDateTime"], "2024-02-29T10:00")
            self.assertEqual(finished["modelStep"], 3)
            assert_finite_numbers(self, finished)
        finally:
            adapter.close()

    def test_calendar_window_exact_stop_and_failed_selection_preserves_run(self):
        adapter = GreenLightGymAdapter()
        try:
            records = [
                {
                    "time": index * 300,
                    "global radiation": max(0, 500 * math.sin((index / 12 - 6) * math.pi / 12)),
                    "wind speed": 2,
                    "air temperature": 12 + index / 1000,
                    "sky temperature": 5,
                    "??": 0,
                    "CO2 concentration": 450,
                    "day number": index / 288,
                    "RH": 75,
                }
                for index in range(433)
            ]
            prepared = adapter.prepare_uploaded_weather(records)
            for start, end in ((33300, 36000), (0, 86400), (85500, 86400)):
                with self.subTest(start=start, end=end):
                    window = {
                        **DEFAULT_WINDOW,
                        "startSeconds": start,
                        "endSeconds": end,
                    }
                    adapter.reset(
                        {
                            "scenario": "uploaded",
                            "_prepared_weather": prepared,
                            "_weather_id": "calendar-test",
                            "runWindow": window,
                        }
                    )
                    self.assertAlmostEqual(adapter.core.hour_of_day, start % 86400 / 3600)
                    self.assertAlmostEqual(adapter.core.x[27], start / 86400)
                    self.assertAlmostEqual(
                        adapter.core.weather_data[0, 1],
                        records[start // 300]["air temperature"],
                    )
                    finished = adapter.step({"steps": 192, "mode": "auto"})
                    expected = (end - start) // 900
                    self.assertEqual(finished["modelStep"], expected)
                    self.assertEqual(finished["runProgress"]["percent"], 100)
                    self.assertTrue(finished["episode"]["terminated"])
                    self.assertEqual(
                        finished["runProgress"]["currentDateTime"],
                        finished["runWindow"]["endDateTime"],
                    )
                    self.assertAlmostEqual(adapter.core.x[27], end / 86400, places=7)
                    self.assertEqual(finished["outputDefinitions"]["forcingIndex"], expected - 1)
                    self.assertEqual(adapter.step({"steps": 1})["modelStep"], expected)
                    assert_finite_numbers(self, finished)
            before = adapter.snapshot()
            invalid = {**DEFAULT_WINDOW, "endSeconds": 87300}
            with self.assertRaises(ValueError):
                adapter.reset(
                    {
                        "scenario": "uploaded",
                        "_prepared_weather": prepared,
                        "runWindow": invalid,
                    }
                )
            self.assertEqual(adapter.snapshot(), before)
            real_make = adapter._make_environment

            def broken_make(*args, **kwargs):
                env = real_make(*args, **kwargs)
                env.reset = lambda **_: (_ for _ in ()).throw(RuntimeError("candidate failed"))
                return env

            with (
                patch.object(adapter, "_make_environment", side_effect=broken_make),
                self.assertRaises(RuntimeError),
            ):
                adapter.reset(
                    {
                        "scenario": "uploaded",
                        "_prepared_weather": prepared,
                        "runWindow": DEFAULT_WINDOW,
                    }
                )
            self.assertEqual(adapter.snapshot(), before)
            app = SimulatorApplication(adapter, requested_engine="glgym")
            weather_id = app.stage_weather(records)["weatherId"]
            app.reset(
                {
                    "scenario": "uploaded",
                    "weatherId": weather_id,
                    "runWindow": DEFAULT_WINDOW,
                    "expectedRevision": 0,
                }
            )
            old_status = app.status()
            for fail_make in (
                broken_make,
                lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("construct failed")),
            ):
                with (
                    patch.object(adapter, "_make_environment", side_effect=fail_make),
                    self.assertRaises(ApiError) as error,
                ):
                    app.reset(
                        {
                            "scenario": "uploaded",
                            "weatherId": weather_id,
                            "runWindow": DEFAULT_WINDOW,
                            "expectedRevision": 1,
                        }
                    )
                self.assertEqual(error.exception.code, "RESET_REJECTED")
                self.assertEqual(app.status(), old_status)
                self.assertIsNone(app.model_error)
            resumed = app.step({"steps": 1, "mode": "auto", "expectedRevision": 1})
            self.assertEqual(resumed["snapshot"]["runId"], old_status["snapshot"]["runId"])
            self.assertEqual(resumed["snapshot"]["modelStep"], 1)
            same_weather = app.reset(
                {
                    "greenhouseConfig": {
                        "schemaVersion": 1,
                        "overrides": {"initialRh": 70},
                    },
                    "expectedRevision": 2,
                }
            )
            self.assertEqual(same_weather["snapshot"]["weatherId"], weather_id)
            self.assertEqual(
                same_weather["snapshot"]["runWindow"]["startSeconds"],
                DEFAULT_WINDOW["startSeconds"],
            )
            self.assertEqual(
                same_weather["snapshot"]["weatherFingerprint"],
                old_status["snapshot"]["weatherFingerprint"],
            )
            pending_id = app.stage_weather(records)["weatherId"]
            self.assertNotEqual(pending_id, weather_id)
            self.assertIn(weather_id, app.uploaded_weather)
            self.assertEqual(app.active_weather_id, weather_id)
            reselected = app.reset(
                {
                    "scenario": "uploaded",
                    "weatherId": weather_id,
                    "runWindow": DEFAULT_WINDOW,
                    "expectedRevision": 3,
                }
            )
            self.assertEqual(reselected["snapshot"]["weatherId"], weather_id)
            self.assertEqual(adapter.reset({"scenario": "spring"})["scenario"], "spring")
        finally:
            adapter.close()


if __name__ == "__main__":
    unittest.main()
