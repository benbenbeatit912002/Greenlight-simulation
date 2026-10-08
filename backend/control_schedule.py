"""Validated, daily source-clock actuator schedules; no model feedback."""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Mapping

from .model_defaults import CONTROL_NAMES


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def validate_schedule(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {"schemaVersion", "entries"}:
        raise ValueError("schedule requires schemaVersion and entries only.")
    if type(value["schemaVersion"]) is not int or value["schemaVersion"] != 1:
        raise ValueError("schedule.schemaVersion must be 1.")
    entries = value["entries"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= 96:
        raise ValueError("Provide 1 to 96 daily schedule rows.")
    result = []
    previous = -1
    for row in entries:
        if not isinstance(row, Mapping) or set(row) != {"time", "controls"}:
            raise ValueError("Each schedule row requires time and controls only.")
        time = row["time"]
        if not isinstance(time, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", time):
            raise ValueError("Schedule times must use HH:MM from 00:00 to 23:45.")
        hour, minute = map(int, time.split(":"))
        absolute = hour * 60 + minute
        if minute % 15 or absolute <= previous:
            raise ValueError("Schedule times must be unique, ordered, and on 15-minute boundaries.")
        controls = row["controls"]
        if not isinstance(controls, Mapping) or set(controls) != set(CONTROL_NAMES):
            raise ValueError("Every schedule row must specify all six actuator commands.")
        if any(
            isinstance(v, bool)
            or not isinstance(v, (int, float))
            or not math.isfinite(v)
            or not 0 <= v <= 1
            for v in controls.values()
        ):
            raise ValueError("Scheduled actuator commands must be numbers between 0 and 1.")
        result.append({"time": time, "controls": {k: float(controls[k]) for k in CONTROL_NAMES}})
        previous = absolute
    if result[0]["time"] != "00:00":
        raise ValueError("The first schedule row must be 00:00 to cover the whole day.")
    return {"schemaVersion": 1, "entries": result}


def scheduled_controls(schedule: Mapping[str, Any], minute_of_day: int) -> dict[str, float]:
    """Zero-order hold on [event, next event), repeating every source day."""
    minute_of_day %= 1440
    selected = schedule["entries"][0]
    for entry in schedule["entries"]:
        hour, minute = map(int, entry["time"].split(":"))
        if hour * 60 + minute > minute_of_day:
            break
        selected = entry
    return dict(selected["controls"])
