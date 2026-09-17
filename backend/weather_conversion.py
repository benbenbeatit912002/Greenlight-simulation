"""Convert validated weather with explicitly supplied upstream unit conversions."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .run_window import coverage


def prepare_uploaded_weather(
    records: Sequence[Mapping[str, Any]],
    *,
    np,
    dt,
    rh_to_vapor_density,
    vapor_density_to_pressure,
    co2_ppm_to_density,
    soil_temperature,
    daily_light_sum,
    compute_is_day,
) -> dict[str, Any]:
    """Convert validated Amsterdam rows to the upstream ten-channel disturbance matrix."""
    if len(records) < 2:
        raise ValueError("Upload at least two weather records.")
    source_time = np.asarray([float(row["time"]) for row in records], dtype=np.float64)
    duration = float(source_time[-1] - source_time[0])
    grid_start = int(np.ceil(source_time[0] / dt) * dt)
    target_time = np.arange(grid_start, source_time[-1] + 1, dt, dtype=np.float64)
    target_count = len(target_time)
    prediction_rows = int(0.5 * 86400 / dt)
    if duration < 36 * 3600:
        raise ValueError("Provide at least 36 hours of weather coverage for a GreenLight run.")
    bounds = coverage(int(source_time[0]), int(source_time[-1]))
    if bounds["latestEndSeconds"] <= bounds["earliestStartSeconds"]:
        raise ValueError(
            "Upload a complete source day plus 12 hours of look-ahead; the file currently has no usable simulation window."
        )

    def interpolate(column: str) -> Any:
        values = np.asarray([float(row[column]) for row in records], dtype=np.float64)
        return np.interp(target_time, source_time, values)

    weather = np.zeros((target_count, 10), dtype=np.float64)
    weather[:, 0] = interpolate("global radiation")
    weather[:, 1] = interpolate("air temperature")
    relative_humidity = interpolate("RH")
    vapor_density = rh_to_vapor_density(weather[:, 1], relative_humidity)
    weather[:, 2] = vapor_density_to_pressure(weather[:, 1], vapor_density)
    weather[:, 3] = co2_ppm_to_density(weather[:, 1], interpolate("CO2 concentration")) * 1e6
    weather[:, 4] = interpolate("wind speed")
    weather[:, 5] = interpolate("sky temperature")
    # Preserve source-year seconds for seasonal inputs and whole-day context.
    weather[:, 6] = soil_temperature(target_time)
    raw_radiation = np.asarray([float(row["global radiation"]) for row in records])
    raw_light_sum = daily_light_sum(source_time, raw_radiation, 86400)
    weather[:, 7] = np.interp(target_time, source_time, raw_light_sum)
    weather[:, 8], weather[:, 9] = compute_is_day(weather[:, 0], dt)
    weather[:, 0][weather[:, 0] < 1e-10] = 0
    if not np.isfinite(weather).all():
        raise ValueError("The converted weather contains non-finite values.")
    season_length = int(((len(weather) - prediction_rows) * dt) // 86400)
    if season_length < 1:
        raise ValueError("The uploaded weather must cover at least one model day.")
    return {
        "weather": weather,
        "seasonLengthDays": season_length,
        "sourceStartSeconds": float(records[0]["time"]),
        "sourceEndSeconds": float(records[-1]["time"]),
        "recordCount": len(records),
        "modelRowCount": len(weather),
        "predHorizonDays": 0.5,
        "gridStartSeconds": grid_start,
        "coverage": bounds,
    }
