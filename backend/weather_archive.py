"""Validate NASA hourly weather and prepare bounded GreenLight forcing windows.

No network, file writes, model fitting or missing-data imputation occurs here.
Hourly source means are retained. Five-minute expansion is explicitly a hold.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

PARAMETER_UNITS = {
    "ALLSKY_SFC_SW_DWN": "MJ/hr",
    "ALLSKY_SFC_LW_DWN": "MJ/hr",
    "T2M": "C",
    "RH2M": "%",
    "WS2M": "m/s",
    "CLOUD_AMT": "%",
}
COLUMNS = (
    "timestamp_utc",
    "air_temperature_c",
    "relative_humidity_pct",
    "wind_speed_2m_m_s",
    "shortwave_w_m2",
    "longwave_w_m2",
    "sky_temperature_c",
    "cloud_fraction",
)


def source_url(site, year):
    if type(year) is not int or not 2001 <= year < datetime.now(timezone.utc).year:
        raise ValueError("Choose a completed year from 2001 onward.")
    for key, limit in (("latitude", 90), ("longitude", 180)):
        value = site[key]
        if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > limit:
            raise ValueError(f"Invalid {key}.")
    return "https://power.larc.nasa.gov/api/temporal/hourly/point?" + urlencode(
        {
            "parameters": ",".join(PARAMETER_UNITS),
            "community": "AG",
            "latitude": site["latitude"],
            "longitude": site["longitude"],
            "start": f"{year}0101",
            "end": f"{year}1231",
            "format": "JSON",
            "time-standard": "UTC",
        }
    )


def _hour_values(data, key, fill):
    values = {name: data[name][key] for name in PARAMETER_UNITS}
    if any(
        type(v) not in (int, float) or not math.isfinite(v) or v == fill for v in values.values()
    ):
        raise ValueError(f"Missing or non-finite NASA value at {key}.")
    if (
        not -90 <= values["T2M"] <= 65
        or not 0 <= values["RH2M"] <= 100
        or not 0 <= values["CLOUD_AMT"] <= 100
        or not 0 <= values["WS2M"] <= 100
        or not 0 <= values["ALLSKY_SFC_SW_DWN"] <= 7.2
        or not 0 < values["ALLSKY_SFC_LW_DWN"] <= 3.6
    ):
        raise ValueError(f"NASA value outside supported physical bounds at {key}.")
    return values


def convert_hourly(payload, year):
    """Require a complete UTC year, including every leap-day hour when applicable."""
    if payload["header"]["time_standard"].upper() != "UTC":
        raise ValueError("Source time standard must be UTC.")
    if {k: payload["parameters"][k]["units"] for k in PARAMETER_UNITS} != PARAMETER_UNITS:
        raise ValueError("NASA units changed; inspect them before converting.")
    start, end = datetime(year, 1, 1), datetime(year + 1, 1, 1)
    hours = int((end - start).total_seconds() // 3600)
    timestamps = [start + timedelta(hours=i) for i in range(hours)]
    expected = {t.strftime("%Y%m%d%H") for t in timestamps}
    data = payload["properties"]["parameter"]
    for name in PARAMETER_UNITS:
        if set(data[name]) != expected:
            raise ValueError(f"Incomplete or unexpected hourly timestamps for {name} in {year}.")
    rows = []
    for timestamp in timestamps:
        v = _hour_values(data, timestamp.strftime("%Y%m%d%H"), payload["header"]["fill_value"])
        sw, lw = (v[name] * 1e6 / 3600 for name in ("ALLSKY_SFC_SW_DWN", "ALLSKY_SFC_LW_DWN"))
        rows.append(
            dict(
                zip(
                    COLUMNS,
                    (
                        timestamp.strftime("%Y-%m-%dT%H:00:00Z"),
                        v["T2M"],
                        v["RH2M"],
                        v["WS2M"],
                        sw,
                        lw,
                        (lw / 5.670374419e-8) ** 0.25 - 273.15,
                        v["CLOUD_AMT"] / 100,
                    ),
                )
            )
        )
    return rows


def summarize(rows):
    return {
        "rows": len(rows),
        "firstTimestampUtc": rows[0]["timestamp_utc"],
        "lastTimestampUtc": rows[-1]["timestamp_utc"],
        "missingHours": 0,
        "imputedValues": 0,
        "ranges": {
            key: {"min": min(r[key] for r in rows), "max": max(r[key] for r in rows)}
            for key in COLUMNS[1:]
        },
    }


def greenlight_window(rows, start, *, hours=96, co2_ppm=400.0, utc_offset_hours=0):
    """Expand UTC archive hours to a fixed-offset Amsterdam-format window.

    Include the end record, so the consumer can reserve its 12-hour look-ahead.
    CO2 is an explicit assumption, not downloaded weather. No cross-year windows.
    """
    if start.tzinfo is not None or start.minute or start.second or start.microsecond:
        raise ValueError("Start must be a naive whole source-clock hour.")
    if (
        type(utc_offset_hours) not in (int, float)
        or not math.isfinite(utc_offset_hours)
        or not -12 <= utc_offset_hours <= 14
        or utc_offset_hours * 4 % 1
    ):
        raise ValueError("Use a fixed UTC offset from -12 to +14 in quarter-hour increments.")
    if type(hours) is not int or not 36 <= hours <= 30 * 24:
        raise ValueError("Weather window must be 36 to 720 whole hours.")
    if (
        type(co2_ppm) not in (int, float)
        or not math.isfinite(co2_ppm)
        or not 100 <= co2_ppm <= 2000
    ):
        raise ValueError("CO2 assumption must be 100 to 2000 ppm.")
    end = start + timedelta(hours=hours)
    if end.year != start.year:
        raise ValueError("Choose a window within one source year.")
    by_time = {row["timestamp_utc"]: row for row in rows}
    if len(by_time) != len(rows):
        raise ValueError("Duplicate archive timestamps.")
    columns = (
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
    result = []
    for step in range(hours * 12 + 1):
        time = start + timedelta(minutes=5 * step)
        utc_time = time - timedelta(hours=utc_offset_hours)
        key = utc_time.strftime("%Y-%m-%dT%H:00:00Z")
        if key not in by_time:
            raise ValueError(f"Missing source hour: {key}. No extrapolation is allowed.")
        row = by_time[key]
        result.append(
            dict(
                zip(
                    columns,
                    (
                        int((time - datetime(time.year, 1, 1)).total_seconds()),
                        row["shortwave_w_m2"],
                        row["wind_speed_2m_m_s"],
                        row["air_temperature_c"],
                        row["sky_temperature_c"],
                        row["cloud_fraction"],
                        co2_ppm,
                        time.timetuple().tm_yday,
                        row["relative_humidity_pct"],
                    ),
                )
            )
        )
    return result
