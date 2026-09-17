"""Reset orchestration with synthetic environments; no model data is accessed."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from backend.greenlight_adapter import (
    GreenLightGymAdapter,
    PreservedRunResetError,
    default_source_path,
)


def fake_adapter():
    adapter = GreenLightGymAdapter.__new__(GreenLightGymAdapter)
    for name in (
        "parameter_fingerprint",
        "initial_state_fingerprint",
        "configuration_fingerprint",
        "model_identifier",
        "weather_fingerprint",
        "run_id",
    ):
        setattr(adapter, name, "previous-" + name)
    values = {
        "greenhouse_config": {"schemaVersion": 1, "overrides": {}},
        "greenhouse_summary": {"previous": True},
        "mode": "auto",
        "targets": {"dayTemp": 21.5},
        "scenario_key": "spring",
        "weather_id": None,
        "weather_label": None,
        "_custom_weather_active": False,
        "_custom_weather_days": 60,
        "obs": {"previous": True},
        "resources": {"heatKwh": 5.0},
        "history": [{"hour": 1.0}],
        "terminated": False,
        "truncated": False,
        "last_reward": 2.0,
        "last_info": {"previous": True},
        "run_window": None,
        "_uploaded_prepared": None,
        "_pending_previous_environment": None,
        "_default_weather_repository": object(),
    }
    for name, value in values.items():
        setattr(adapter, name, value)
    adapter.core = SimpleNamespace(base_p=[1.0], parameter_provider=SimpleNamespace(base_p=[1.0]))
    adapter.env = Mock(unwrapped=adapter.core)
    new_core = SimpleNamespace(base_p=[1.0], parameter_provider=SimpleNamespace(base_p=[1.0]))
    candidate = Mock(unwrapped=new_core)
    candidate.reset.return_value = ({"candidate": True}, {})
    adapter._make_environment = Mock(return_value=candidate)
    adapter._initialize_run_state = Mock(return_value={"default": True})
    adapter._describe_configuration = Mock()

    def begin_history():
        adapter.run_id = "candidate-run"
        adapter.resources = {"heatKwh": 0.0}
        adapter.history = []

    adapter._begin_run_history = Mock(side_effect=begin_history)
    adapter.snapshot = Mock(return_value={"runId": "candidate-run"})
    return adapter, candidate


class ResetTransactionTests(unittest.TestCase):
    def setUp(self):
        parameters = patch("backend.greenlight_adapter.apply_parameters", return_value=[2.0])
        parameters.start()
        self.addCleanup(parameters.stop)

    def test_success_publishes_candidate_before_closing_previous(self):
        adapter, candidate = fake_adapter()
        previous = adapter.env
        events = []
        adapter.snapshot.side_effect = lambda: (
            events.append("snapshot") or {"runId": "candidate-run"}
        )
        previous.close.side_effect = lambda: events.append("close previous")
        result = adapter.reset({"scenario": "winter", "seed": 123})
        self.assertEqual(events, ["snapshot", "close previous"])
        self.assertEqual(result["runId"], "candidate-run")
        self.assertIs(adapter.env, candidate)
        self.assertEqual(previous.unwrapped.parameter_provider.base_p, [1.0])
        self.assertEqual(candidate.unwrapped.parameter_provider.base_p, [2.0])
        candidate.reset.assert_called_once_with(
            seed=123,
            options={
                "scenario": {
                    "location": "Amsterdam",
                    "growth_year": 2010,
                    "start_day": 1,
                }
            },
        )
        candidate.close.assert_not_called()

    def test_failure_restores_previous_solver_and_bookkeeping(self):
        for stage in ("reset", "initialization", "snapshot"):
            with self.subTest(stage=stage):
                adapter, candidate = fake_adapter()
                previous = adapter.env
                before = adapter._capture_run_state()
                target = {
                    "reset": candidate.reset,
                    "initialization": adapter._initialize_run_state,
                    "snapshot": adapter.snapshot,
                }[stage]
                target.side_effect = RuntimeError("synthetic candidate failure")
                with self.assertRaises(PreservedRunResetError):
                    adapter.reset({"scenario": "winter", "mode": "manual"})
                self.assertIs(adapter.env, previous)
                self.assertEqual(adapter._capture_run_state(), before)
                self.assertIsNone(adapter._pending_previous_environment)
                previous.close.assert_not_called()
                candidate.close.assert_called_once()

    def test_invalid_request_keeps_run_without_creating_environment(self):
        adapter, candidate = fake_adapter()
        before = adapter._capture_run_state()
        with self.assertRaises(ValueError):
            adapter.reset({"scenario": "not-a-scenario", "mode": "manual"})
        self.assertEqual(adapter._capture_run_state(), before)
        adapter._make_environment.assert_not_called()
        candidate.reset.assert_not_called()


class ModelPathTests(unittest.TestCase):
    def test_missing_path_does_not_probe_siblings(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(Path, "is_file") as probe:
            with self.assertRaisesRegex(RuntimeError, "GREENLIGHT_GYM_PATH"):
                default_source_path()
            probe.assert_not_called()

    def test_explicit_path_is_resolved(self):
        with patch.dict(os.environ, {"GREENLIGHT_GYM_PATH": "example-model"}):
            self.assertEqual(default_source_path(), Path("example-model").resolve())
