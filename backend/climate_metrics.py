"""Whole-run climate metrics evaluated on full-model end-of-step samples."""

from __future__ import annotations

import math
from typing import Any, Mapping

from .control_schedule import fingerprint

DEFAULT_LIMITS = {
    "temperatureMin": 15.0,
    "temperatureMax": 34.0,
    "humidityMin": 50.0,
    "humidityMax": 85.0,
}


def validate_limits(value: Any) -> dict[str, float]:
    if not isinstance(value, Mapping) or set(value) != set(DEFAULT_LIMITS):
        raise ValueError("evaluationLimits requires temperatureMin/Max and humidityMin/Max.")
    for key, number in value.items():
        low, high = (-50, 70) if key.startswith("temperature") else (0, 100)
        if (
            isinstance(number, bool)
            or not isinstance(number, (int, float))
            or not low <= number <= high
        ):
            raise ValueError(f"{key} must be a finite number between {low} and {high}.")
    for prefix in ("temperature", "humidity"):
        if value[prefix + "Min"] >= value[prefix + "Max"]:
            raise ValueError(f"{prefix} minimum must be below its maximum.")
    return {key: float(value[key]) for key in DEFAULT_LIMITS}


class ClimateMetrics:
    def __init__(self, limits: Mapping[str, float]):
        self.limits = validate_limits(limits)
        self.samples = 0
        self.minutes = 0.0
        self.temperature_sum = self.humidity_sum = 0.0
        self.temperature_min = self.temperature_max = None
        self.humidity_min = self.humidity_max = None
        self.temperature_outside = self.humidity_outside = self.either_outside = 0.0

    def record(self, temperature: float, humidity: float, minutes: float) -> None:
        if not all(math.isfinite(v) for v in (temperature, humidity, minutes)) or minutes <= 0:
            raise ValueError("Climate metrics require finite states and a positive interval.")
        self.samples += 1
        self.minutes += minutes
        self.temperature_sum += temperature * minutes
        self.humidity_sum += humidity * minutes
        for prefix, value in (("temperature", temperature), ("humidity", humidity)):
            for suffix, operation in (("min", min), ("max", max)):
                old = getattr(self, prefix + "_" + suffix)
                setattr(
                    self, prefix + "_" + suffix, value if old is None else operation(old, value)
                )
        t_out = not self.limits["temperatureMin"] <= temperature <= self.limits["temperatureMax"]
        rh_out = not self.limits["humidityMin"] <= humidity <= self.limits["humidityMax"]
        self.temperature_outside += minutes if t_out else 0
        self.humidity_outside += minutes if rh_out else 0
        self.either_outside += minutes if t_out or rh_out else 0

    def snapshot(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "method": "end-of-step-duration-weighted-v1",
            "limits": dict(self.limits),
            "limitsFingerprint": fingerprint(self.limits),
            "samples": self.samples,
            "evaluatedMinutes": self.minutes,
            "meanTemperature": self.temperature_sum / self.minutes if self.minutes else None,
            "meanHumidity": self.humidity_sum / self.minutes if self.minutes else None,
            "minTemperature": self.temperature_min,
            "maxTemperature": self.temperature_max,
            "minHumidity": self.humidity_min,
            "maxHumidity": self.humidity_max,
            "temperatureOutsideMinutes": self.temperature_outside,
            "humidityOutsideMinutes": self.humidity_outside,
            "eitherOutsideMinutes": self.either_outside,
        }
