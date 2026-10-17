"""Collect yearly NASA POWER weather into data/weather/downloads, without API keys.

Reuses verified raw downloads. Existing files are never overwritten. Output
stays within the simulator. Network requests are sequential and bounded.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.weather_archive import COLUMNS, convert_hourly, source_url, summarize  # noqa: E402

DATA = ROOT / "data" / "weather"
MAX_BYTES = 8 * 1024 * 1024
DEFAULT_COLLECTION = "nasa-power-2023-2024-v1"


def local_path(path):
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(DATA.resolve()):
        raise ValueError("Weather output must stay inside this project's data/weather folder.")
    return resolved


def collection_path(name):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError("Collection name must use lowercase letters, digits and hyphens.")
    return local_path(DATA / "downloads" / name)


def save_new(path, content):
    path = local_path(path)
    if path.exists():
        if path.read_bytes() != content:
            raise FileExistsError(f"Refusing to overwrite existing file: {path.name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def fetch_raw(folder, url):
    raw_path, source_path = local_path(folder / "source.json"), local_path(folder / "request.json")
    if raw_path.exists():
        raw = raw_path.read_bytes()
        meta = json.loads(source_path.read_text(encoding="utf-8"))
        if meta["url"] != url or hashlib.sha256(raw).hexdigest() != meta["sha256"]:
            raise ValueError(
                "Cached request or source hash does not match. Use a new collection folder."
            )
        return raw, meta
    request = Request(url, headers={"User-Agent": "Greenlight-simulation-weather/1.0"})
    with urlopen(request, timeout=45) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("NASA response exceeds the 8 MiB limit.")
    json.loads(raw)
    meta = {
        "url": url,
        "retrievedAtUtc": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    save_new(source_path, json_bytes(meta))
    save_new(raw_path, raw)
    return raw, meta


def collect(site, year, output):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", site["id"]):
        raise ValueError("Site id must use lowercase letters, digits and hyphens.")
    folder = local_path(output / site["id"] / str(year))
    raw, source = fetch_raw(folder, source_url(site, year))
    payload = json.loads(raw)
    rows = convert_hourly(payload, year)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    csv_bytes = buffer.getvalue().encode("utf-8")
    report = {
        "schemaVersion": 1,
        "conversionVersion": "nasa-hourly-utc-v1",
        "provider": "NASA POWER",
        "site": site,
        "year": year,
        "source": source,
        "sourceHeader": payload["header"],
        "sourceGeometry": payload.get("geometry"),
        "sourceUnits": payload["parameters"],
        "hourlySha256": hashlib.sha256(csv_bytes).hexdigest(),
        "quality": summarize(rows),
        "timeStandard": "UTC",
        "cadenceMinutes": 60,
        "dataType": "Gridded satellite/reanalysis, not greenhouse observations",
        "radiationConversion": "MJ/hr multiplied by 1e6/3600 gives W/m2",
        "skyTemperature": "Effective radiative sky temperature from downward longwave; emissivity convention 1",
        "wind": "2 m wind speed, no height adjustment",
        "calibrationReady": False,
        "missingForCalibration": [
            "Measured indoor climate",
            "Actual actuator histories",
            "Greenhouse/crop specification",
        ],
        "reference": "https://power.larc.nasa.gov/docs/referencing/",
    }
    save_new(folder / "hourly.csv", csv_bytes)
    save_new(folder / "manifest.json", json_bytes(report))
    return {
        "site": site["id"],
        "country": site["country"],
        "year": year,
        "status": "validated",
        "path": folder.relative_to(DATA).as_posix(),
        "quality": report["quality"],
        "sourceSha256": source["sha256"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--site", default="all", help="Site id from data/weather/sites.json, or all"
    )
    parser.add_argument("--years", nargs="+", type=int, default=[2023, 2024])
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.collection):
        parser.error("Collection name must use lowercase letters, digits and hyphens.")
    sites = json.loads((DATA / "sites.json").read_text(encoding="utf-8"))["sites"]
    if args.site != "all":
        sites = [s for s in sites if s["id"] == args.site]
    if not sites or len(set(args.years)) != len(args.years) or len(args.years) > 5:
        parser.error("Choose a known site and at most five unique years per invocation.")
    output = collection_path(args.collection)
    results = []
    for site in sites:
        for year in args.years:
            try:
                result = collect(site, year, output)
            except (OSError, ValueError, KeyError) as error:
                result = {"site": site["id"], "year": year, "status": "failed", "error": str(error)}
            results.append(result)
            print(json.dumps({k: v for k, v in result.items() if k != "quality"}), flush=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    save_new(output / f"collection-{stamp}.json", json_bytes({"datasets": results}))
    return 1 if any(r["status"] == "failed" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
