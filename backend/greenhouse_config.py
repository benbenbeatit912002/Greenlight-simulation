"""Run-local, audited subset of GreenLight parameters. Never edits upstream defaults.

Index mapping and derived equations: gl_gym/configs/default_params.py.
Initial states: gl_gym/environments/utils.py::init_state.
Software bounds are validation limits, not agronomic recommendations.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

SCHEMA_VERSION = 1
# key, group, English label, Chinese label, unit, low, high, parameter index
FIELDS = (
    ("floorArea", "geometry", "Floor area", "地板面積", "m²", 1, 2000, 46),
    (
        "coverArea",
        "geometry",
        "Cover area including walls",
        "覆蓋面積（含側牆）",
        "m²",
        1,
        10000,
        47,
    ),
    (
        "mainHeight",
        "geometry",
        "Main-compartment height",
        "主空氣室高度",
        "m",
        1,
        15,
        48,
    ),
    (
        "totalHeight",
        "geometry",
        "Mean greenhouse height",
        "溫室平均高度",
        "m",
        1.1,
        20,
        49,
    ),
    (
        "roofVentArea",
        "equipment",
        "Maximum roof vent opening area",
        "屋頂通風口最大面積",
        "m²",
        0,
        2000,
        55,
    ),
    ("ventHeight", "equipment", "Vent opening height", "通風口高度", "m", 0.1, 3, 56),
    (
        "boilerPower",
        "equipment",
        "Boiler capacity per floor area",
        "每平方米最大供暖功率",
        "W/m²",
        0,
        500,
        108,
    ),
    (
        "co2Capacity",
        "equipment",
        "CO₂ capacity per floor area",
        "每平方米最大 CO₂ 供應量",
        "mg/m²/s",
        0,
        20,
        109,
    ),
    (
        "lampPower",
        "equipment",
        "Top-lamp electrical capacity",
        "頂部補光燈最大電功率",
        "W/m²",
        0,
        400,
        172,
    ),
    (
        "roofParTransmission",
        "cover",
        "Cover PAR transmission",
        "覆蓋材料 PAR 透射率",
        "0–1",
        0,
        0.87,
        69,
    ),
    (
        "roofNirTransmission",
        "cover",
        "Cover NIR transmission",
        "覆蓋材料 NIR 透射率",
        "0–1",
        0,
        0.87,
        68,
    ),
    ("roofThickness", "cover", "Cover thickness", "覆蓋材料厚度", "mm", 0.5, 30, 73),
    (
        "roofConductivity",
        "cover",
        "Cover thermal conductivity",
        "覆蓋材料熱傳導係數",
        "W/m/K",
        0.05,
        5,
        71,
    ),
    (
        "initialAirTemp",
        "initial",
        "Initial main-air temperature",
        "主空氣室初始溫度",
        "°C",
        5,
        40,
        None,
    ),
    (
        "initialRh",
        "initial",
        "Initial main-air relative humidity",
        "主空氣室初始相對濕度",
        "%",
        10,
        100,
        None,
    ),
    (
        "initialCo2",
        "initial",
        "Initial main-air CO₂",
        "主空氣室初始 CO₂",
        "ppm",
        100,
        3000,
        None,
    ),
    (
        "initialLeaf",
        "crop",
        "Initial leaf dry mass",
        "初始葉片乾重",
        "g/m²",
        1,
        500,
        None,
    ),
    (
        "initialStem",
        "crop",
        "Initial stem dry mass",
        "初始莖部乾重",
        "g/m²",
        1,
        3000,
        None,
    ),
    (
        "initialFruit",
        "crop",
        "Initial fruit dry mass",
        "初始果實乾重",
        "g/m²",
        0,
        3000,
        None,
    ),
    (
        "initialCanopyTemp",
        "crop",
        "Initial canopy temperature",
        "初始冠層溫度",
        "°C",
        5,
        45,
        None,
    ),
    (
        "initialCanopy24h",
        "crop",
        "Initial 24h canopy-temperature state",
        "初始冠層 24 小時溫度狀態",
        "°C",
        5,
        45,
        None,
    ),
    (
        "initialTempSum",
        "crop",
        "Initial crop temperature sum",
        "初始作物積溫",
        "°C day",
        0,
        5000,
        None,
    ),
)
FIELD_MAP = {row[0]: row for row in FIELDS}
STATE_MAP = {
    "initialAirTemp": (2, 1),
    "initialLeaf": (23, 1000),
    "initialStem": (24, 1000),
    "initialFruit": (25, 1000),
    "initialCanopyTemp": (4, 1),
    "initialCanopy24h": (21, 1),
    "initialTempSum": (26, 1),
}


def field_metadata():
    return [
        {"key": k, "group": g, "en": en, "zh": zh, "unit": u, "min": lo, "max": hi}
        for k, g, en, zh, u, lo, hi, _ in FIELDS
    ]


def validate_config(request: Any) -> dict:
    if not isinstance(request, Mapping) or set(request) != {
        "schemaVersion",
        "overrides",
    }:
        raise ValueError("greenhouseConfig requires schemaVersion and overrides only.")
    if type(request["schemaVersion"]) is not int or request["schemaVersion"] != SCHEMA_VERSION:
        raise ValueError("Unsupported greenhouse configuration schema.")
    overrides = request["overrides"]
    if not isinstance(overrides, Mapping) or set(overrides) - set(FIELD_MAP):
        raise ValueError("Unknown greenhouse setting. Use only the supported fields.")
    result = {}
    for key, value in overrides.items():
        low, high = FIELD_MAP[key][5:7]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not low <= value <= high
            or not math.isfinite(value)
        ):
            raise ValueError(f"{key} must be a finite number from {low:g} to {high:g}.")
        result[key] = float(value)
    return {"schemaVersion": SCHEMA_VERSION, "overrides": result}


def parameter_values(p) -> dict[str, float]:
    values = {row[0]: float(p[row[7]]) for row in FIELDS if row[7] is not None}
    values["boilerPower"] /= float(p[46])
    values["co2Capacity"] /= float(p[46])
    values["roofThickness"] *= 1000
    return values


def apply_parameters(base, request):
    """Copy the upstream vector; update only mapped fields and their dependencies."""
    if len(base) != 208:
        raise ValueError("Unsupported GreenLight parameter layout.")
    overrides = validate_config(request)["overrides"]
    values = {**parameter_values(base), **overrides}
    if values["coverArea"] < values["floorArea"]:
        raise ValueError("coverArea must be at least floorArea; area fields are independent.")
    if values["totalHeight"] - values["mainHeight"] < 0.1 - 1e-9:
        raise ValueError(
            "Mean greenhouse height must exceed main-compartment height by at least 0.1 m."
        )
    if values["roofVentArea"] > values["floorArea"]:
        raise ValueError(
            "Roof vent area must not exceed floor area in this supported configuration."
        )
    if overrides.get("initialLeaf", 0) * 1000 > float(base[144]):
        raise ValueError("Initial leaf mass exceeds the model's maximum leaf mass (LAI limit).")
    for key, reflection in (("roofParTransmission", 66), ("roofNirTransmission", 65)):
        if values[key] + float(base[reflection]) > 1 + 1e-8:
            raise ValueError("Cover transmission plus inherited reflection must not exceed one.")
    p = base.copy()
    for key, value in overrides.items():
        index = FIELD_MAP[key][7]
        if index is not None and key not in (
            "boilerPower",
            "co2Capacity",
            "roofThickness",
        ):
            p[index] = value
    if "roofThickness" in overrides:
        p[73] = values["roofThickness"] / 1000
    if {"floorArea", "boilerPower"} & overrides.keys():
        p[108] = values["boilerPower"] * p[46]
    if {"floorArea", "co2Capacity"} & overrides.keys():
        p[109] = values["co2Capacity"] * p[46]
    # Same dependency equations as upstream default_params.py. No recomputation
    # for an unchanged setting: {} must reproduce the exact upstream vector.
    if "mainHeight" in overrides:
        p[112] = p[48] * p[111] * p[23]
        p[122] = p[48]
    if {"mainHeight", "totalHeight"} & overrides.keys():
        p[120] = (p[49] - p[48]) * p[111] * p[23]
        p[123] = p[49] - p[48]
    return p


def initial_values(x, *, sat_vp, co2_density_to_ppm):
    values = {key: float(x[index]) / scale for key, (index, scale) in STATE_MAP.items()}
    values["initialRh"] = float(x[15]) / float(sat_vp(x[2])) * 100
    values["initialCo2"] = float(co2_density_to_ppm(x[2], x[0] * 1e-6))
    return values


def apply_initial_state(x, request, *, sat_vp, co2_density_to_ppm, co2_ppm_to_density):
    overrides = request["overrides"]
    defaults = initial_values(x, sat_vp=sat_vp, co2_density_to_ppm=co2_density_to_ppm)
    result = x.copy()
    for key, (index, scale) in STATE_MAP.items():
        if key in overrides:
            result[index] = overrides[key] * scale
    # Temperature-only edits preserve original main-air RH and ppm, not densities.
    # Top air, surfaces, soil and other unexposed thermal states stay upstream defaults.
    if {"initialAirTemp", "initialRh"} & overrides.keys():
        result[15] = overrides.get("initialRh", defaults["initialRh"]) / 100 * sat_vp(result[2])
    if {"initialAirTemp", "initialCo2"} & overrides.keys():
        result[0] = (
            co2_ppm_to_density(result[2], overrides.get("initialCo2", defaults["initialCo2"])) * 1e6
        )
    return result
