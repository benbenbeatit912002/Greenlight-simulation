"""Portable run evidence. No uploaded workbook or local path is bundled."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from copy import deepcopy

from .model_defaults import CONTROL_NAMES, SCENARIOS
from .run_window import STEP_SECONDS, source_datetime

FORMAT = "greenlight-run/2"
LEGACY_FORMAT = "greenlight-run/1"
COLUMNS = (
    "step",
    "elapsed_min",
    "source_minute_of_day",
    "indoor_temp_C",
    "indoor_rh_pct",
    "indoor_co2_ppm",
    "canopy_temp_C",
    "pipe_temp_C",
    "above_canopy_W_m2",
    "canopy_PAR_umol_m2_s",
    "LAI_m2_m2",
    "fruit_dry_mass_g_m2",
    "outdoor_temp_C",
    "outdoor_rh_pct",
    "outdoor_radiation_W_m2",
    "wind_m_s",
    "heat_kWh_m2_total",
    "lamp_kWh_m2_total",
    "co2_kg_m2_total",
    "cost_EUR_m2_total",
    "temperature_outside_min_total",
    "humidity_outside_min_total",
    "either_outside_min_total",
    "preceding_mode",
    *("requested_" + name for name in CONTROL_NAMES),
    *("applied_" + name for name in CONTROL_NAMES),
    *(f"state_x{i}" for i in range(28)),
    *(f"forcing_d{i}" for i in range(10)),
)
WINDOW_KEYS = ("sourceYear", "timeConvention", "startSeconds", "endSeconds")
RECIPE_FILE = "settings.json"
SERIES_FILE = "timeseries.csv"


class RunArchive:
    """Record every accepted physical step, independently of the display history."""

    def __init__(self, reset, identity, *, step_seconds, horizon_steps):
        if step_seconds != STEP_SECONDS:
            raise ValueError("Run archives require a native timestep of exactly 900 seconds.")
        if type(horizon_steps) is not int or horizon_steps < 1:
            raise ValueError("Invalid native run horizon.")
        self.horizon_steps = horizon_steps
        self.reset = deepcopy(reset)
        self.identity = dict(identity)
        self.commands = []
        self.count = 0
        self.stream = io.StringIO(newline="")
        self.writer = csv.writer(self.stream, lineterminator="\n")
        self.writer.writerow(COLUMNS)

    def calendar(self):
        if self.reset["scenario"] == "uploaded":
            w = self.reset["runWindow"]
            year, start, end = w["sourceYear"], w["startSeconds"], w["endSeconds"]
            convention = w["timeConvention"]
        else:
            preset = SCENARIOS[self.reset["scenario"]]
            year = preset["growth_year"]
            # The pinned loader slices at start_day * 86400 from year-second zero.
            start = preset["start_day"] * 86400
            end = start + self.horizon_steps * STEP_SECONDS
            convention = "bundled-source-clock"
        return {
            "sourceYear": year,
            "timeConvention": convention,
            "start": source_datetime(year, start),
            "plannedEnd": source_datetime(year, end),
            "capturedEnd": source_datetime(year, start + (self.count - 1) * STEP_SECONDS),
        }

    def append(self, step, values, command):
        if step != self.count or len(values) != len(COLUMNS) - 1:
            raise ValueError("Incomplete or out-of-order full-model record.")
        if (step == 0) != (command is None):
            raise ValueError("A command is required for each completed interval, not at reset.")
        self.writer.writerow((step, *values))
        self.count += 1
        if command is None:
            return
        if self.commands and self.commands[-1]["command"] == command:
            self.commands[-1]["steps"] += 1
        else:
            self.commands.append({"steps": 1, "command": deepcopy(command)})

    def bundle(self):
        series = self.stream.getvalue().encode("utf-8")
        reset = dict(self.reset)
        if reset["mode"] != "schedule" and not any(
            s["command"]["mode"] == "schedule" for s in self.commands
        ):
            reset.pop("schedule", None)
        recipe = {
            "format": FORMAT,
            "stepSeconds": STEP_SECONDS,
            "calendar": self.calendar(),
            "completedSteps": self.count - 1,
            "reset": reset,
            "identity": self.identity,
            "commands": self.commands,
            "seriesSha256": hashlib.sha256(series).hexdigest(),
        }
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=3) as out:
            out.writestr(RECIPE_FILE, json.dumps(recipe, indent=2, allow_nan=False) + "\n")
            out.writestr(SERIES_FILE, series)
        return buffer.getvalue()
