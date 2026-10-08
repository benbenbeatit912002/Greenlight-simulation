"""Opt-in full-model robustness checks against downloaded public weather.

Fetch first with examples/fetch_public_weather.py. This is not model calibration
or a proof of physical/predictive stability. No source repository is written.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from backend.greenlight_adapter import GreenLightGymAdapter  # noqa: E402
from examples.fetch_public_weather import SITES  # noqa: E402


def schedule():
    names = ("uBoil", "uCO2", "uThScr", "uVent", "uLamp", "uBlScr")
    rows = (
        ("00:00", (0.35, 0, 1, 0.05, 0, 1)),
        ("06:00", (0.5, 0.1, 0.5, 0.1, 0, 0)),
        ("10:00", (0.15, 0.1, 0, 0.25, 0, 0)),
        ("18:00", (0.35, 0, 1, 0.05, 0, 1)),
    )
    return {
        "schemaVersion": 1,
        "entries": [{"time": time, "controls": dict(zip(names, values))} for time, values in rows],
    }


def run(adapter, request, mode, batch):
    initial = adapter.reset({**request, "mode": mode, "schedule": schedule()})
    previous = initial["resources"]
    result = initial
    while result["modelStep"] < 288:
        result = adapter.step({"mode": mode, "steps": min(batch, 288 - result["modelStep"])})
        assert adapter._np.isfinite(adapter.core.x).all(), "Non-finite model state"
        assert not result["episode"]["truncated"], "Solver failure"
        assert all(result["resources"][k] >= v for k, v in previous.items())
        assert all(0 <= v <= 1 for v in result["controls"].values())
        previous = result["resources"]
    assert result["elapsedMinutes"] == 4320
    assert result["climateMetrics"]["evaluatedMinutes"] == 4320
    assert result["climateMetrics"]["samples"] == 288
    assert not result["strategyChanged"]
    assert result["episode"]["terminated"]
    assert adapter.step({"steps": 1})["modelStep"] == 288
    return initial, result


def main():
    output = ROOT / ".runtime" / "controller-weather"
    adapter = GreenLightGymAdapter()
    results = {}
    try:
        for name in SITES:
            data = json.loads((output / f"{name}.json").read_text(encoding="utf-8"))
            prepared = adapter.prepare_uploaded_weather(data["records"])
            start = int(data["records"][0]["time"])
            request = {
                "scenario": "uploaded",
                "_prepared_weather": prepared,
                "_weather_id": name,
                "_weather_label": f"NASA POWER {name}",
                "seed": 42,
                "greenhouseConfig": {"schemaVersion": 1, "overrides": {}},
                "runWindow": {
                    "sourceYear": 2023,
                    "timeConvention": "source-local-standard",
                    "startSeconds": start,
                    "endSeconds": start + 72 * 3600,
                },
            }
            auto_initial, auto = run(adapter, request, "auto", 1)
            plan_initial, planned = run(adapter, request, "schedule", 1)
            _, batched = run(adapter, request, "schedule", 48)
            for key in (
                "initialStateFingerprint",
                "weatherFingerprint",
                "configurationFingerprint",
                "modelVersion",
            ):
                assert auto_initial[key] == plan_initial[key], f"Unmatched {key}"
            for key in ("indoor", "resources", "climateMetrics", "controlHistory"):
                assert planned[key] == batched[key], f"Playback batching affected {key}"
            results[name] = {
                "source": data["metadata"],
                "checks": "Finite state, no solver truncation, bounded controls, monotonic resources, identical starting conditions, exact 72-hour endpoint, batch invariance passed.",
                "auto": auto,
                "schedule": planned,
            }
            print(
                json.dumps(
                    {
                        "site": name,
                        "auto": auto["climateMetrics"],
                        "scheduled": planned["climateMetrics"],
                        "heatingKwhM2": [
                            auto["resources"]["heatKwh"],
                            planned["resources"]["heatKwh"],
                        ],
                    }
                ),
                flush=True,
            )
    finally:
        adapter.close()
    (output / "full-model-results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
