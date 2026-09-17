"""Source-calendar window rules, independent of the optional scientific runtime."""

from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from typing import Any, Mapping

STEP_SECONDS = 900
DAY_SECONDS = 86400
LOOKAHEAD_SECONDS = 43200


def coverage(source_start: int, source_end: int) -> dict[str, int]:
    # The upstream lamp controller needs the daily radiation sum. Only offer
    # complete source days; no missing midnight context is treated as zero.
    earliest = ((source_start + DAY_SECONDS - 1) // DAY_SECONDS) * DAY_SECONDS
    latest = min(
        (source_end - LOOKAHEAD_SECONDS) // STEP_SECONDS * STEP_SECONDS,
        source_end // DAY_SECONDS * DAY_SECONDS,
    )
    return {
        "sourceStartSeconds": source_start,
        "sourceEndSeconds": source_end,
        "earliestStartSeconds": earliest,
        "latestEndSeconds": latest,
        "stepSeconds": STEP_SECONDS,
        "lookaheadSeconds": LOOKAHEAD_SECONDS,
        "warmupSeconds": 0,
    }


def validate_window(request: Any, bounds: Mapping[str, int]) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        raise ValueError(
            "Choose a simulation window and specify the source year and time convention."
        )
    required = {"sourceYear", "timeConvention", "startSeconds", "endSeconds"}
    if set(request) != required:
        raise ValueError(
            "runWindow requires sourceYear, timeConvention, startSeconds and endSeconds only."
        )
    year = request["sourceYear"]
    if type(year) is not int or not 1900 <= year <= 2100:
        raise ValueError("sourceYear must be an integer from 1900 to 2100.")
    convention = request["timeConvention"]
    if convention not in ("source-local-standard", "UTC"):
        raise ValueError(
            "Choose source-local-standard or UTC. Daylight-saving clock changes are not supported."
        )
    start, end = request["startSeconds"], request["endSeconds"]
    if any(type(value) is not int or value % STEP_SECONDS for value in (start, end)):
        raise ValueError("Start and end must align to 15-minute source-clock boundaries.")
    if start >= end:
        raise ValueError("End must be after start by at least 15 minutes.")
    year_seconds = (366 if calendar.isleap(year) else 365) * DAY_SECONDS
    if bounds["sourceEndSeconds"] > year_seconds or start < 0 or end > year_seconds:
        raise ValueError(
            "Weather timestamps exceed the selected source year; check the year and leap-day data."
        )
    if start < bounds["earliestStartSeconds"] or end > bounds["latestEndSeconds"]:
        raise ValueError(
            "The selected window needs uploaded weather from its first midnight through its last day, plus 12 hours after the end. No weather is extrapolated."
        )
    return {
        **dict(request),
        "stepSeconds": STEP_SECONDS,
        "totalSteps": (end - start) // STEP_SECONDS,
        "durationMinutes": (end - start) // 60,
        "lookaheadSeconds": LOOKAHEAD_SECONDS,
        "warmupSeconds": 0,
        "initialization": "GreenLight default states at the selected start; no warm-up",
        "startDateTime": source_datetime(year, start),
        "endDateTime": source_datetime(year, end),
    }


def source_datetime(year: int, seconds: int) -> str:
    """Naive source-clock string: never apply the host's timezone or DST."""
    return (datetime(year, 1, 1) + timedelta(seconds=seconds)).isoformat(timespec="minutes")
