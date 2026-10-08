"""Fetch bounded NASA POWER examples without keys; keep provenance and reject gaps.

Run from the repository: python -B examples/fetch_public_weather.py --site all
Outputs are project-local raw JSON, converted records and CSV for Excel import.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
PARAMETERS = ("ALLSKY_SFC_SW_DWN", "ALLSKY_SFC_LW_DWN", "T2M", "RH2M", "WS2M", "CLOUD_AMT")
COLUMNS = (
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
SITES = {
    "amsterdam-winter": {
        "latitude": 52.37,
        "longitude": 4.90,
        "start": "2023-01-15",
        "utcOffsetHours": 1,
    },
    "almeria-summer": {
        "latitude": 36.84,
        "longitude": -2.46,
        "start": "2023-07-15",
        "utcOffsetHours": 1,
    },
    "taipei-summer": {
        "latitude": 25.03,
        "longitude": 121.57,
        "start": "2023-07-15",
        "utcOffsetHours": 8,
    },
}


def source_url(site):
    start = datetime.fromisoformat(site["start"])
    query = {
        "parameters": ",".join(PARAMETERS),
        "community": "AG",
        "latitude": site["latitude"],
        "longitude": site["longitude"],
        "start": (start - timedelta(days=1)).strftime("%Y%m%d"),
        "end": (start + timedelta(days=4)).strftime("%Y%m%d"),
        "format": "JSON",
        "time-standard": "UTC",
    }
    return "https://power.larc.nasa.gov/api/temporal/hourly/point?" + urlencode(query)


def convert(payload, site):
    units = {key: payload["parameters"][key]["units"] for key in PARAMETERS}
    expected = {
        "ALLSKY_SFC_SW_DWN": "MJ/hr",
        "ALLSKY_SFC_LW_DWN": "MJ/hr",
        "T2M": "C",
        "RH2M": "%",
        "WS2M": "m/s",
        "CLOUD_AMT": "%",
    }
    if units != expected or payload["header"]["time_standard"].upper() != "UTC":
        raise ValueError(
            "NASA units or time standard changed; inspect the source before conversion."
        )
    data = payload["properties"]["parameter"]
    start = datetime.fromisoformat(site["start"])
    end = start + timedelta(days=4)
    year_start = datetime(start.year, 1, 1)
    records = []
    # Hourly averages are held over each source hour. This makes no claim of
    # measured 5-minute variability and never bridges a missing source hour.
    timestamp = start
    while timestamp <= end:
        source_time = timestamp - timedelta(hours=site["utcOffsetHours"])
        key = source_time.strftime("%Y%m%d%H")
        try:
            values = {name: data[name][key] for name in PARAMETERS}
        except KeyError as exc:
            raise ValueError(f"Missing NASA source hour: {key}") from exc
        if any(
            type(v) not in (int, float)
            or not math.isfinite(v)
            or v == payload["header"]["fill_value"]
            for v in values.values()
        ):
            raise ValueError(f"Missing or invalid NASA value at {key}")
        if (
            values["ALLSKY_SFC_SW_DWN"] < 0
            or values["ALLSKY_SFC_LW_DWN"] <= 0
            or values["WS2M"] < 0
            or not 0 <= values["RH2M"] <= 100
            or not 0 <= values["CLOUD_AMT"] <= 100
        ):
            raise ValueError(f"NASA source value outside supported physical range at {key}")
        radiation = values["ALLSKY_SFC_SW_DWN"] * 1e6 / 3600
        longwave = values["ALLSKY_SFC_LW_DWN"] * 1e6 / 3600
        sky = (longwave / 5.670374419e-8) ** 0.25 - 273.15
        records.append(
            dict(
                zip(
                    COLUMNS,
                    (
                        int((timestamp - year_start).total_seconds()),
                        radiation,
                        values["WS2M"],
                        values["T2M"],
                        sky,
                        values["CLOUD_AMT"] / 100,
                        400.0,
                        timestamp.timetuple().tm_yday,
                        values["RH2M"],
                    ),
                )
            )
        )
        timestamp += timedelta(minutes=5)
    return records


def fetch_site(name, output):
    site = SITES[name]
    url = source_url(site)
    with urlopen(url, timeout=60) as response:
        raw = response.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError("Unexpectedly large NASA response.")
    payload = json.loads(raw)
    records = convert(payload, site)
    metadata = {
        "provider": "NASA POWER",
        "url": url,
        "retrievedAt": datetime.now(timezone.utc).isoformat(),
        "rawSha256": hashlib.sha256(raw).hexdigest(),
        "site": site,
        "sourceYear": 2023,
        "timeConvention": "source-local-standard",
        "sourceCadenceMinutes": 60,
        "outputCadenceMinutes": 5,
        "conversion": "Hourly values held on 5-minute grid; no gap filling or extrapolation. Fixed standard offset, no DST.",
        "radiationConversion": "NASA MJ/hr to W/m²: multiply by 1e6/3600.",
        "skyTemperature": "Effective sky temperature derived from downward longwave irradiance using Stefan-Boltzmann law, emissivity convention 1.",
        "co2Ppm": 400,
        "co2Assumption": "Fixed example assumption, not a NASA measurement.",
        "wind": "NASA wind at 2 m; no height correction.",
        "soilTemperature": "The current simulator retains upstream soilTempNl; this is not a calibrated local soil model.",
        "unusedColumn": "?? retains NASA cloud fraction; the simulator does not consume it.",
        "dataType": "Gridded satellite/reanalysis product, not a greenhouse-site station observation.",
        "sourceHeader": payload["header"],
        "sourceUnits": payload["parameters"],
    }
    output.mkdir(parents=True, exist_ok=True)
    stem = output / name
    stem.with_suffix(".raw.json").write_bytes(raw)
    stem.with_suffix(".json").write_text(
        json.dumps({"metadata": metadata, "records": records}, indent=2), encoding="utf-8"
    )
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(records)
    stem.with_suffix(".csv").write_text(buffer.getvalue(), encoding="utf-8")
    print(f"{name}: {len(records)} rows, source SHA-256 {metadata['rawSha256']}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", choices=[*SITES, "all"], default="all")
    parser.add_argument("--output", type=Path, default=ROOT / ".runtime" / "controller-weather")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT):
        parser.error("Output must stay inside Greenlight-simulation.")
    for name in SITES if args.site == "all" else [args.site]:
        fetch_site(name, output)


if __name__ == "__main__":
    main()
