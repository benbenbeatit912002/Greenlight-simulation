"""Reproduce the Davis July failures in an isolated process using the pinned full model.

The one-expression numerical counterfactual is diagnostic only. No package file,
dashboard default, live environment, or archived weather row is changed.
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.model_defaults import CONTROL_NAMES  # noqa: E402
from examples.collect_weather import DATA, DEFAULT_COLLECTION, json_bytes, save_new  # noqa: E402
from examples.weather_runs import load_year, new_adapter, prepare_request  # noqa: E402

FORCING = (
    "globalWm2",
    "airC",
    "vapourPa",
    "co2Mgm3",
    "windMs",
    "skyC",
    "soilC",
    "lightSumMJm2day",
    "day",
    "smoothDay",
)
STATES = (
    "co2Air",
    "co2Top",
    "tAir",
    "tTop",
    "tCan",
    "tCovIn",
    "tCovOut",
    "tThScr",
    "tFloor",
    "tPipe",
    "tSo1",
    "tSo2",
    "tSo3",
    "tSo4",
    "tSo5",
    "vpAir",
    "vpTop",
    "tLamp",
    "tIntLamp",
    "tGrowPipe",
    "tBlScr",
    "tCan24",
    "cBuf",
    "cLeaf",
    "cStem",
    "cFruit",
    "tCanSum",
    "timeDays",
)


def named(keys, values):
    return dict(zip(keys, (float(x) for x in values), strict=True))


def source_clock(year, seconds, offset):
    tz = timezone(timedelta(hours=offset))
    return (datetime(year, 1, 1, tzinfo=tz) + timedelta(seconds=seconds)).isoformat()


def finite_or_none(value):
    number = float(value)
    return number if math.isfinite(number) else None


def probe_graphs():
    import casadi as ca
    from gl_gym.models.GreenLight import aux_states, ode

    x, u, d, p = (ca.SX.sym(n, size) for n, size in (("x", 28), ("u", 6), ("d", 10), ("p", 208)))
    rhs = ode.ODE(x, u, d, p)
    original = aux_states.cond
    replaced = []

    def checked_cond(hec, vp1, vp2):
        if not ca.is_equal(vp1, x[16]):
            return original(hec, vp1, vp2)
        # Only mvTopCovIn uses the above-screen pressure as its first argument.
        replaced.append(1)
        z = 0.1 * (vp2 - vp1)
        b = ca.exp(ca.if_else(z >= 0, -z, z))
        sigmoid = ca.if_else(z >= 0, b / (1 + b), 1 / (1 + b))
        return sigmoid * 6.4e-9 * hec * (vp1 - vp2)

    # Build a separate symbolic graph, then restore the original symbol immediately.
    # This script runs offline in its own process, never in the HTTP application.
    with patch.object(aux_states, "cond", checked_cond):
        alternate = ode.ODE(x, u, d, p)
    if replaced != [1] or aux_states.cond is not original:
        raise RuntimeError("Expected exactly one top-cover condensation substitution.")
    z = 0.1 * (aux_states.satVP(x[5]) - x[16])
    cols = [ca.jacobian(f, x)[5, 5] for f in (rhs, alternate)]
    probe = ca.Function("cover_probe", [x, u, d, p], [z, *cols, rhs, alternate])
    # Same 900 s boundary/controls/forcing/CVODES options as gl-gym 0.3.2 define_model.
    solve = ca.integrator(
        "stable_cover",
        "cvodes",
        {"x": x, "u": u, "p": ca.vertcat(d, p), "ode": alternate},
        0,
        900,
        {"abstol": 1e-4, "reltol": 1e-4, "max_num_steps": 70000},
    )
    return probe, solve


def evaluate(probe, x, u, d, p):
    import numpy as np

    z, raw_j, stable_j, raw_rhs, stable_rhs = probe(x, u, d, p)
    left, right = np.asarray(raw_rhs), np.asarray(stable_rhs)
    return {
        "exponent": float(z),
        "logFloat64Max": math.log(sys.float_info.max),
        "originalJac55": finite_or_none(raw_j),
        "stableJac55": finite_or_none(stable_j),
        "originalJac55Finite": math.isfinite(float(raw_j)),
        "stableJac55Finite": math.isfinite(float(stable_j)),
        "rhsMaxAbsDifference": finite_or_none(np.max(np.abs(left - right))),
    }


def capture(adapter, request, year, offset):
    core = adapter.core
    t = int(core.timestep)
    seconds = request["runWindow"]["startSeconds"] + t * 900
    return {
        "stepBefore": t,
        "start": source_clock(year, seconds, offset),
        "state": named(STATES, core.x),
        "weatherThisInterval": named(FORCING, core.weather_data[t]),
        "previousApplied": named(CONTROL_NAMES, core.u),
        "requested": named(CONTROL_NAMES, adapter._controller_action()),
        "indoorRhPct": float(adapter.obs["IndoorClimateObservations"][2]),
    }


def single_step_probe(adapter, case, probe, stable):
    import casadi as ca
    import numpy as np

    frame = case["lastFourAndAttempt"][-1]
    x = list(frame["state"].values())
    d = list(frame["weatherThisInterval"].values())
    u, p = list(case["attemptedApplied"].values()), adapter.core.p.copy()
    inputs = {"x0": ca.DM(x), "u": ca.DM(u), "p": ca.vertcat(ca.DM(d), p)}
    comparison = {"atStart": evaluate(probe, x, u, d, p)}
    try:
        unchanged = adapter.core.F(**inputs)["xf"].full().ravel()
        comparison["originalEndpointFinite"] = bool(np.isfinite(unchanged).all())
    except RuntimeError as exc:
        comparison["originalEndpointFinite"] = False
        comparison["originalSolverMessage"] = str(exc).splitlines()[-1]
    try:
        fixed = stable(**inputs)["xf"].full().ravel()
        comparison["stableEndpointFinite"] = bool(np.isfinite(fixed).all())
        if comparison["stableEndpointFinite"]:
            comparison["atStableEndpoint"] = evaluate(probe, fixed, u, d, p)
            comparison["stableEndpointCoverC"] = float(fixed[5])
            comparison["stableEndpointTopVapourPa"] = float(fixed[16])
    except RuntimeError as exc:
        comparison["stableEndpointFinite"] = False
        comparison["stableSolverMessage"] = str(exc).splitlines()[-1]
    return comparison


def trace(adapter, year, offset, probe, stable):
    rows, manifest = load_year("davis-us", year)
    req = prepare_request(adapter, rows, "davis-us", year, 7, utc_offset_hours=offset)
    initial = adapter.reset({**req, "mode": "auto"})
    frames = deque(maxlen=5)
    result = {
        "year": year,
        "clock": f"UTC{offset:+d} fixed",
        "site": "davis-us",
        "sourceSha256": manifest["source"]["sha256"],
        "collection": DEFAULT_COLLECTION,
        "model": initial["modelVersion"],
        "weather": initial["weatherFingerprint"],
        "initial": initial["initialStateFingerprint"],
        "parameters": initial["parameterFingerprint"],
        "configuration": initial["configurationFingerprint"],
        "window": initial["runWindow"],
        "seed": req["seed"],
        "mode": "auto",
    }
    for step in range(initial["runWindow"]["totalSteps"]):
        frames.append(capture(adapter, req, year, offset))
        try:
            adapter.step({"steps": 1, "mode": "auto"})
        except RuntimeError as exc:
            result.update(
                status="failed",
                completedSteps=step,
                error=str(exc),
                lastFourAndAttempt=list(frames),
                attemptedApplied=named(CONTROL_NAMES, adapter.core.u),
            )
            result["matchedStepExperiment"] = single_step_probe(adapter, result, probe, stable)
            return result
    return {**result, "status": "completed", "completedSteps": int(adapter.core.timestep)}


CASE_MARKER = "DAVIS_CASE_JSON: "


def emit_case(year):
    """One child per year so the native solver's stderr has an unambiguous owner."""
    offset = json.loads((DATA / "sites.json").read_text())["standardUtcOffsetsHours"]["davis-us"]
    adapter = new_adapter()
    try:
        probe, stable = probe_graphs()
        case = trace(adapter, year, offset, probe, stable)
    finally:
        adapter.close()
    print(CASE_MARKER + json.dumps(case, allow_nan=False))


def classify(case, messages):
    matched = case.get("matchedStepExperiment", {})
    row55 = bool(re.search(r"NaN detected for output jac_ode_x[^\n]*\(row 5, col 5\)", messages))
    times = re.findall(
        r"At t = ([0-9.eE+\-]+) and h = [^,]+, the corrector convergence test failed", messages
    )
    contrast = (
        case.get("status") == "failed"
        and case.get("completedSteps") == {2023: 44, 2024: 244}.get(case["year"])
        and matched.get("originalEndpointFinite") is False
        and "CV_CONV_FAILURE" in matched.get("originalSolverMessage", "")
        and matched.get("stableEndpointFinite") is True
        and row55
    )
    return {
        "verdict": "matched numerical contrast reproduced" if contrast else "inconclusive",
        "row5Col5NanReportedByThisCase": row55,
        "correctorFailureSeconds": sorted({float(t) for t in times}),
    }


def isolated_case(year):
    proc = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            "from scripts.diagnose_davis import emit_case; import sys; emit_case(int(sys.argv[1]))",
            str(year),
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    result_lines = [
        line.removeprefix(CASE_MARKER)
        for line in proc.stdout.splitlines()
        if line.startswith(CASE_MARKER)
    ]
    if len(result_lines) != 1:
        raise RuntimeError("No unique model trace returned from the case process.")
    case = json.loads(result_lines[0])
    other_stdout = "\n".join(
        line for line in proc.stdout.splitlines() if not line.startswith(CASE_MARKER)
    )
    case.update(classify(case, proc.stderr + "\n" + other_stdout))
    return case


def main():
    cases = [isolated_case(year) for year in (2023, 2024)]
    report = {
        "scope": "Offline fixed-state numerical counterfactual, not calibration, a production fix or a saved successful run.",
        "nonfinitePolicy": "null represents a non-finite derivative; use adjacent Finite flags.",
        "modelStateUnits": "Temperatures in degrees Celsius, water vapour pressure in Pa. State order follows the pinned ODE.",
        "cases": cases,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = DATA / "reports" / f"davis-cover-diagnostic-{stamp}.json"
    save_new(path, json_bytes(report))
    for case in cases:
        print(
            json.dumps(
                {
                    k: case.get(k)
                    for k in (
                        "year",
                        "completedSteps",
                        "verdict",
                        "correctorFailureSeconds",
                        "matchedStepExperiment",
                    )
                }
            )
        )
    print(path.relative_to(ROOT))
    return 0 if all(c["verdict"] == "matched numerical contrast reproduced" for c in cases) else 2


if __name__ == "__main__":
    raise SystemExit(main())
