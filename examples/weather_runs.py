"""Shared, offline full-model checks for the public weather archive."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime

from backend.weather_archive import convert_hourly, greenlight_window
from examples.collect_weather import DEFAULT_COLLECTION, collection_path, local_path


def load_year(site, year, *, collection=DEFAULT_COLLECTION):
    folder = local_path(collection_path(collection) / site / str(year))
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    raw = (folder / "source.json").read_bytes()
    csv = (folder / "hourly.csv").read_bytes()
    if (
        hashlib.sha256(raw).hexdigest() != manifest["source"]["sha256"]
        or hashlib.sha256(csv).hexdigest() != manifest["hourlySha256"]
    ):
        raise ValueError("Archive checksum mismatch.")
    return convert_hourly(json.loads(raw), year), manifest


def new_adapter():
    if os.environ.get("GREENLIGHT_GYM_PATH"):
        raise ValueError("Unset GREENLIGHT_GYM_PATH to test the pinned public package.")
    from backend.greenlight_adapter import GreenLightGymAdapter

    return GreenLightGymAdapter()


def prepare_request(adapter, rows, site, year, month, hours=72, overrides=None, utc_offset_hours=0):
    start = datetime(year, month, 15)
    records = greenlight_window(rows, start, hours=hours + 24, utc_offset_hours=utc_offset_hours)
    seconds = records[0]["time"]
    return {
        "scenario": "uploaded",
        "_prepared_weather": adapter.prepare_uploaded_weather(records),
        "_weather_id": f"nasa-{site}-{year}-{month}",
        "_weather_label": f"NASA POWER {site} UTC{utc_offset_hours:+g}",
        "seed": 42,
        "greenhouseConfig": {"schemaVersion": 1, "overrides": overrides or {}},
        "runWindow": {
            "sourceYear": year,
            "timeConvention": "source-local-standard" if utc_offset_hours else "UTC",
            "startSeconds": seconds,
            "endSeconds": seconds + hours * 3600,
        },
    }


class ModelRunError(RuntimeError):
    def __init__(self, message, evidence):
        super().__init__(message)
        self.evidence = dict(evidence)


def _step_sequence(adapter, initial, mode, controls, evidence):
    count = evidence["steps"]
    values, previous = [], initial["resources"]
    for step in range(count):
        command = {"steps": 1, "mode": mode}
        if controls:
            command["controls"] = controls(step)
        snapshot = adapter.step(command)
        if not adapter._np.isfinite(adapter.core.x).all() or snapshot["episode"]["truncated"]:
            raise RuntimeError("Non-finite or truncated model run.")
        if snapshot["modelStep"] != step + 1:
            raise RuntimeError("Model stopped before the requested endpoint.")
        if any(
            snapshot["resources"][key] < previous[key] for key in ("heatKwh", "lampKwh", "co2Kg")
        ):
            raise RuntimeError("Cumulative resource decreased.")
        if not all(0 <= v <= 1 for v in snapshot["controls"].values()):
            raise RuntimeError("Applied control outside [0, 1].")
        # Fit/metrics use unrounded upstream observations, not dashboard text.
        climate = adapter.obs["IndoorClimateObservations"]
        values.append([float(climate[1]), float(climate[2])])
        previous = snapshot["resources"]
        evidence["completedSteps"] = step + 1
    if not snapshot["episode"]["terminated"] or adapter.step({"steps": 1})["modelStep"] != count:
        raise RuntimeError("Incorrect endpoint handling.")
    return values, snapshot


def run_steps(adapter, request, *, controls=None):
    mode = "manual" if controls else "auto"
    initial = adapter.reset({**request, "mode": mode})
    evidence = {
        "modelVersion": initial["modelVersion"],
        "weatherFingerprint": initial["weatherFingerprint"],
        "initialStateFingerprint": initial["initialStateFingerprint"],
        "configurationFingerprint": initial["configurationFingerprint"],
        "steps": initial["runWindow"]["totalSteps"],
        "runWindow": initial["runWindow"],
        "completedSteps": 0,
    }
    try:
        values, snapshot = _step_sequence(adapter, initial, mode, controls, evidence)
    except (ValueError, RuntimeError) as error:
        steps = evidence["completedSteps"]
        raise ModelRunError(
            f"Run failed after {steps} complete steps ({steps / 4:g} hours): {error}", evidence
        ) from error
    return values, {
        **evidence,
        "resources": snapshot["resources"],
        "climateMetrics": snapshot["climateMetrics"],
    }
