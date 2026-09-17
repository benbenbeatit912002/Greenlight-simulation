"""Guard the upstream loader against implicitly reading another year's data."""

from __future__ import annotations

import csv
import math
from pathlib import Path


def require_single_year_coverage(path: Path, *, start_day, n_days, pred_horizon) -> None:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        times = [float(row["time"]) for row in csv.DictReader(handle)]
    if len(times) < 2 or not all(math.isfinite(t) for t in times):
        raise ValueError("Weather time values must be finite and cover at least two records.")
    dt = (times[-1] - times[0]) / (len(times) - 1)
    if times[0] != 0 or dt <= 0 or any(abs(b - a - dt) > 1e-6 for a, b in zip(times, times[1:])):
        raise ValueError(
            "The upstream loader requires regular weather starting at year-second zero."
        )
    required = (
        math.ceil(start_day * 86400 / dt)
        + math.ceil(n_days * 86400 / dt)
        + math.ceil(pred_horizon * 86400 / dt)
        + 1
    )
    if start_day < 0 or required > len(times):
        raise ValueError(
            "This scenario needs weather beyond the selected CSV. Reading another year automatically is disabled; select an earlier scenario."
        )


def single_year_loader(upstream):
    def load(**kwargs):
        location = str(kwargs["location"])
        year = int(kwargs["growth_year"])
        if location != "Amsterdam" or year != 2010:
            raise ValueError("Only the explicitly authorized Amsterdam/2010.csv is enabled.")
        path = Path(kwargs["weather_data_dir"]) / location / f"{year}.csv"
        require_single_year_coverage(
            path,
            **{key: kwargs[key] for key in ("start_day", "n_days", "pred_horizon")},
        )
        return upstream(**kwargs)

    return load
