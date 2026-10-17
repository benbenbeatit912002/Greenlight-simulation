"""Run 72-hour January/July numerical checks with the full model, not calibration."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

from examples.collect_weather import (  # noqa: E402
    DATA,
    DEFAULT_COLLECTION,
    collection_path,
    json_bytes,
    save_new,
)
from examples.weather_runs import (  # noqa: E402
    ModelRunError,
    load_year,
    new_adapter,
    prepare_request,
    run_steps,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="all")
    parser.add_argument("--years", type=int, nargs="+", default=[2023, 2024])
    parser.add_argument("--months", type=int, nargs="+", default=[1, 7])
    parser.add_argument("--clock", choices=["local-standard", "UTC"], default="local-standard")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    args = parser.parse_args()
    collection_path(args.collection)
    catalog = json.loads((DATA / "sites.json").read_text(encoding="utf-8"))
    sites = catalog["sites"]
    if args.site != "all":
        sites = [site for site in sites if site["id"] == args.site]
    if not sites or any(m not in range(1, 13) for m in args.months):
        parser.error("Choose a known site and months from 1 to 12.")
    offsets = catalog["standardUtcOffsetsHours"]
    if args.clock == "local-standard" and any(s["id"] not in offsets for s in sites):
        parser.error("Add each site's fixed standard UTC offset to sites.json before model checks.")
    adapter = new_adapter()
    results = []
    try:
        for site in sites:
            for year in args.years:
                for month in args.months:
                    offset = offsets[site["id"]] if args.clock == "local-standard" else 0
                    result = {
                        "site": site["id"],
                        "year": year,
                        "month": month,
                        "utcOffsetHours": offset,
                        "collection": args.collection,
                    }
                    stage = "weather"
                    try:
                        rows, manifest = load_year(site["id"], year, collection=args.collection)
                        result["sourceSha256"] = manifest["source"]["sha256"]
                        stage = "preparation"
                        request = prepare_request(
                            adapter, rows, site["id"], year, month, utc_offset_hours=offset
                        )
                        stage = "simulation"
                        _, metrics = run_steps(adapter, request)
                        result.update(status="completed", **metrics)
                    except (OSError, KeyError, ValueError, RuntimeError) as error:
                        if isinstance(error, ModelRunError):
                            result.update(error.evidence)
                        result.update(status="failed", stage=stage, error=str(error))
                    results.append(result)
                    print(
                        json.dumps(
                            {k: result[k] for k in ("site", "year", "month", "status")}
                            | {"error": result.get("error")}
                        ),
                        flush=True,
                    )
    finally:
        adapter.close()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    save_new(
        DATA / "reports" / f"full-model-{stamp}.json",
        json_bytes(
            {
                "scope": "Numerical execution only. No greenhouse observations or calibration.",
                "clock": args.clock,
                "collection": args.collection,
                "fixedOffsetOnly": True,
                "daylightSaving": False,
                "soil": "Upstream Netherlands soil-temperature assumption unchanged",
                "co2PpmAssumption": 400,
                "runs": results,
            }
        ),
    )
    return 1 if any(r["status"] == "failed" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
