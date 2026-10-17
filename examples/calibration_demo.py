"""Synthetic parameter-recovery experiment using only the full GreenLight model.

This is an optimizer plumbing test, NOT calibration against a real greenhouse.
It estimates one deliberately hidden boiler capacity from generated T/RH data.
The fitted value is never applied to the dashboard or upstream source files.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from examples.collect_weather import (  # noqa: E402
    DATA,
    DEFAULT_COLLECTION,
    collection_path,
    json_bytes,
    save_new,
)
from examples.weather_runs import load_year, new_adapter, prepare_request, run_steps  # noqa: E402


def controls(step):
    hour = (step // 4) % 24
    return {
        "uBoil": 0.45 if hour < 6 or hour >= 18 else 0.25,
        "uCO2": 0,
        "uThScr": 0.8 if hour < 6 or hour >= 18 else 0.2,
        "uVent": 0.05,
        "uLamp": 0,
        "uBlScr": 0,
    }


def main():
    import numpy as np
    from scipy.optimize import least_squares

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    args = parser.parse_args()
    collection_path(args.collection)
    archives = {
        year: load_year("amsterdam-nl", year, collection=args.collection) for year in (2023, 2024)
    }
    adapter = new_adapter()
    site, truth, initial_guess = "amsterdam-nl", 180.0, 260.0
    warmup_steps = 12 * 4
    calls = 0
    provenance = {}
    requests = {}

    def simulate(power, year):
        nonlocal calls
        calls += 1
        if calls > 40:
            raise RuntimeError("Experiment exceeded its 40-run budget.")
        request = {
            **requests[year],
            "greenhouseConfig": {
                "schemaVersion": 1,
                "overrides": {"boilerPower": float(power)},
            },
        }
        values, identity = run_steps(adapter, request, controls=controls)
        return np.asarray(values)[warmup_steps:], identity

    def metrics(prediction, observed):
        residual = prediction - observed
        return {
            name: {
                "rmse": float(np.sqrt(np.mean(residual[:, i] ** 2))),
                "mae": float(np.mean(np.abs(residual[:, i]))),
                "bias": float(np.mean(residual[:, i])),
            }
            for i, name in enumerate(("temperatureC", "rhPercentagePoints"))
        }

    try:
        for year in (2023, 2024):
            rows, manifest = archives[year]
            requests[year] = prepare_request(adapter, rows, site, year, 1, hours=48)
            provenance[str(year)] = manifest["source"]["sha256"]
        generated_train, train_identity = simulate(truth, 2023)
        # These noise levels are declared experiment settings, not sensor specifications.
        rng = np.random.default_rng(42)
        observed_train = generated_train + rng.normal(size=generated_train.shape) * [0.1, 0.5]
        before_train, _ = simulate(initial_guess, 2023)

        def objective(parameter):
            prediction, _ = simulate(float(parameter[0]), 2023)
            return ((prediction - observed_train) / [0.2, 1.0]).ravel()

        fit = least_squares(
            objective,
            [initial_guess],
            bounds=([80.0], [320.0]),
            loss="soft_l1",
            diff_step=0.002,
            max_nfev=12,
            ftol=1e-5,
            xtol=1e-5,
            gtol=1e-5,
        )
        power = float(fit.x[0])
        after_train, fitted_identity = simulate(power, 2023)
        # Hold-out observations are generated only after fitting, and never enter objective().
        generated_test, test_identity = simulate(truth, 2024)
        observed_test = generated_test + rng.normal(size=generated_test.shape) * [0.1, 0.5]
        before_test, _ = simulate(initial_guess, 2024)
        after_test, _ = simulate(power, 2024)
        before, after = metrics(before_test, observed_test), metrics(after_test, observed_test)
        passed = (
            bool(fit.success)
            and abs(power - truth) < 5.0
            and all(after[k]["rmse"] < 0.5 * before[k]["rmse"] for k in before)
        )
        report = {
            "scope": "Synthetic recovery test only; not real-world calibration or independent validation",
            "collection": args.collection,
            "method": "Bounded least squares, soft-L1 loss; one parameter; fixed known open-loop controls",
            "parameter": "boilerPower",
            "unit": "W/m2",
            "bounds": [80, 320],
            "syntheticTruth": truth,
            "initialGuess": initial_guess,
            "estimate": power,
            "success": passed,
            "optimizerSuccess": bool(fit.success),
            "optimizerMessage": fit.message,
            "modelRuns": calls,
            "maxModelRuns": 40,
            "training": {"year": 2023, "start": "2023-01-15T00:00:00Z", "hours": 48},
            "holdout": {"year": 2024, "start": "2024-01-15T00:00:00Z", "hours": 48},
            "excludedWarmupHoursEachRun": 12,
            "syntheticNoiseStd": {"temperatureC": 0.1, "rhPct": 0.5},
            "residualScales": {"temperatureC": 0.2, "rhPct": 1.0},
            "trainingBefore": metrics(before_train, observed_train),
            "trainingAfter": metrics(after_train, observed_train),
            "holdoutBefore": before,
            "holdoutAfter": after,
            "sourceHashes": provenance,
            "truthModel": train_identity,
            "fittedModel": fitted_identity,
            "holdoutModel": test_identity,
            "limitations": [
                "Same simulator generates and fits the targets (inverse crime)",
                "One parameter; all other parameters and controls assumed known",
                "No sensor alignment, structural error or real-greenhouse uncertainty tested",
                "No fitted setting saved to the dashboard",
            ],
        }
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        save_new(DATA / "reports" / f"synthetic-fit-{stamp}.json", json_bytes(report))
        print(
            json.dumps(
                {
                    k: report[k]
                    for k in (
                        "scope",
                        "success",
                        "estimate",
                        "modelRuns",
                        "holdoutBefore",
                        "holdoutAfter",
                    )
                }
            ),
            flush=True,
        )
        return 0 if passed else 1
    finally:
        adapter.close()


if __name__ == "__main__":
    raise SystemExit(main())
