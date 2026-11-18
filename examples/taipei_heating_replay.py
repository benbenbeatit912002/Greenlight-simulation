"""Compare two heating start times using the same Taipei weather and verify both runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.application import SimulatorApplication  # noqa: E402
from backend.model_defaults import CONTROL_NAMES  # noqa: E402
from backend.weather_upload import validate_weather_workbook  # noqa: E402
from examples.weather_runs import new_adapter  # noqa: E402
from scripts.replay_run import project_destination, read_bundle, replay  # noqa: E402


def daily_plan(start):
    rows = []
    for time in ("00:00", "04:00", "06:00", "08:00", "18:00"):
        heating = 0.25 if start <= time < "08:00" else 0.0
        vent = 0.8 if "08:00" <= time < "18:00" else 0.35
        rows.append(
            {
                "time": time,
                "controls": dict(zip(CONTROL_NAMES, (heating, 0, 0, vent, 0, 0), strict=True)),
            }
        )
    return {"schemaVersion": 1, "entries": rows}


def compare(workbook):
    rows = validate_weather_workbook(workbook, include_records=True)["_records"]
    start = int(rows[0]["time"])
    app = SimulatorApplication(new_adapter(), requested_engine="greenlight2")
    bundles = {}
    try:
        weather_id = app.stage_weather(rows)["weatherId"]
        identity = None
        results = {}
        for time in ("04:00", "06:00"):
            initial = app.reset(
                {
                    "mode": "schedule",
                    "scenario": "uploaded",
                    "seed": 42,
                    "weatherId": weather_id,
                    "greenhouseConfig": {"schemaVersion": 1, "overrides": {}},
                    "schedule": daily_plan(time),
                    "evaluationLimits": {
                        "temperatureMin": 18,
                        "temperatureMax": 30,
                        "humidityMin": 50,
                        "humidityMax": 85,
                    },
                    "runWindow": {
                        "sourceYear": 2023,
                        "timeConvention": "source-local-standard",
                        "startSeconds": start,
                        "endSeconds": start + 48 * 3600,
                    },
                }
            )["snapshot"]
            snapshot = app.step({"steps": 192, "mode": "schedule"})["snapshot"]
            if snapshot["modelStep"] != 192 or not snapshot["episode"]["terminated"]:
                raise RuntimeError("The 48-hour window did not finish.")
            blob = app.export({"runId": initial["runId"], "expectedRevision": app.revision})
            recipe = read_bundle(blob)
            if identity is not None and recipe["identity"] != identity:
                raise RuntimeError("The two scenarios do not use identical comparison conditions.")
            identity = recipe["identity"]
            verified, _ = replay(recipe, workbook)
            m = verified["climateMetrics"]
            results[time] = {
                "meanIndoorC": m["meanTemperature"],
                "meanIndoorRhPct": m["meanHumidity"],
                "heatingKWhPerM2": app.engine.resources["heatKwh"],
                "temperatureOutsideHours": m["temperatureOutsideMinutes"] / 60,
                "humidityOutsideHours": m["humidityOutsideMinutes"] / 60,
                "completedSteps": verified["modelStep"],
                "seriesSha256": recipe["seriesSha256"],
                "exactReplay": True,
            }
            bundles[time.replace(":", "") + ".zip"] = blob
        return {
            "timeConvention": "Taipei source local standard time (UTC+8)",
            "window": initial["runWindow"],
            "limits": m["limits"],
            "identity": identity,
            "runs": results,
        }, bundles
    finally:
        app.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--save-dir", type=Path, help="Optional new directory for the two ZIPs and summary."
    )
    args = parser.parse_args()
    output = project_destination(args.save_dir) if args.save_dir else None
    report, bundles = compare((ROOT / "templates/weather-taipei-summer.xlsx").read_bytes())
    encoded = json.dumps(report, indent=2, allow_nan=False)
    if output:
        project_destination(output).mkdir(parents=True, exist_ok=False)
        for name, blob in bundles.items():
            with project_destination(output / name).open("xb") as handle:
                handle.write(blob)
        with project_destination(output / "summary.json").open("x", encoding="utf-8") as handle:
            handle.write(encoded + "\n")
    print(encoded)


if __name__ == "__main__":
    main()
