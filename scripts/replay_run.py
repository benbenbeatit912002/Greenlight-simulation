"""Re-run a dashboard export offline using the same installed GreenLight model."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import sys
import zipfile
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.application import ApiError, SimulatorApplication  # noqa: E402
from backend.model_defaults import DEFAULT_TARGETS  # noqa: E402
from backend.mpc_controller import POLICY, devices  # noqa: E402
from backend.run_archive import FORMAT, LEGACY_FORMAT, RECIPE_FILE, SERIES_FILE  # noqa: E402
from backend.weather_upload import MAX_UPLOAD_BYTES, validate_weather_workbook  # noqa: E402

MIB = 1024 * 1024
MAX_STEPS = 60 * 96 + 1  # Full preset horizon plus the upstream final boundary.
RESET_KEYS = {"mode", "seed", "scenario", "targets", "greenhouseConfig", "evaluationLimits"}
HASH = r"[0-9a-f]{64}"
FINGERPRINTS = {
    "weatherFingerprint",
    "initialStateFingerprint",
    "parameterFingerprint",
    "configurationFingerprint",
    "limitsFingerprint",
}


def validate_identity(identity):
    if not isinstance(identity, dict) or not isinstance(identity.get("modelVersion"), str):
        raise ValueError("Missing modelVersion in run identity.")
    model = re.fullmatch(
        rf"gl-gym2@[\w.-]+\+(sha256\.{HASH}|git\.[0-9a-f]{{40}})\.adapter\.[\w.-]+\.params\.({HASH})",
        identity["modelVersion"],
    )
    if not model or model[2] != identity.get("parameterFingerprint"):
        raise ValueError("Unidentified modelVersion or mismatched parameters.")
    hashes = FINGERPRINTS | ({"sourceSha256"} if model[1].startswith("git.") else set())
    if set(identity) != hashes | {"modelVersion", "costModelId"} or not all(
        isinstance(identity[k], str) and re.fullmatch(HASH, identity[k]) for k in hashes
    ):
        raise ValueError("Incomplete source or scientific fingerprints.")
    if identity["costModelId"] != "greenlight-gym2-variable-costs":
        raise ValueError("Unknown costModelId.")


def project_destination(value, root=ROOT):
    """Anchor new outputs in this project, without traversing symlinks or junctions."""
    root = root.resolve(strict=True)
    value = Path(value)
    candidate = value if value.is_absolute() else root / value
    if not candidate.is_relative_to(root):
        raise ValueError("Output must be inside the simulator folder.")
    parts = candidate.relative_to(root).parts
    if (
        not parts
        or any(
            p in {".", ".."}
            or p.endswith((" ", "."))
            or ":" in p
            or PureWindowsPath(p).is_reserved()
            for p in parts
        )
        or parts[0].casefold() in {".git", ".venv", ".codex", ".agents"}
    ):
        raise ValueError("Choose a new output inside the simulator folder.")
    path = root
    for part in parts:
        path /= part
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(
            stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
        ):
            raise ValueError("Linked output paths are not allowed.")
    return path


def read_bounded(path, limit):
    with Path(path).open("rb") as handle:
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("Input file exceeds the size limit.")
    return raw


def validate_mpc_reset(reset):
    if reset["mode"] == "mpc":
        if reset.get("mpcPolicy") != POLICY or not devices(reset.get("mpcDevices")):
            raise ValueError("Missing devices or unsupported MPC policy in this run.")
    elif {"mpcPolicy", "mpcDevices"} & reset.keys():
        raise ValueError("Unexpected MPC settings in a non-MPC run.")


def validate_recipe(recipe):
    expected = {
        "format",
        "stepSeconds",
        "completedSteps",
        "reset",
        "identity",
        "commands",
        "seriesSha256",
    }
    if not isinstance(recipe, dict) or recipe.get("format") not in (FORMAT, LEGACY_FORMAT):
        raise ValueError("Unrecognized run settings format.")
    if recipe["format"] == FORMAT:
        expected.add("calendar")
        cal = recipe.get("calendar")
        if (
            not isinstance(cal, dict)
            or set(cal) != {"sourceYear", "timeConvention", "start", "plannedEnd", "capturedEnd"}
            or type(cal["sourceYear"]) is not int
            or not all(
                isinstance(cal[k], str)
                for k in ("timeConvention", "start", "plannedEnd", "capturedEnd")
            )
        ):
            raise ValueError("Missing or invalid source calendar.")
    if set(recipe) != expected:
        raise ValueError("Unrecognized run settings format.")
    steps = recipe["completedSteps"]
    if type(steps) is not int or not 1 <= steps <= MAX_STEPS or recipe["stepSeconds"] != 900:
        raise ValueError("Invalid physical timestep or run length.")
    reset = recipe["reset"]
    if not isinstance(reset, dict) or not RESET_KEYS <= set(reset) <= RESET_KEYS | {
        "runWindow",
        "schedule",
        "mpcDevices",
        "mpcPolicy",
    }:
        raise ValueError("Run settings contain missing or unsupported reset fields.")
    if not isinstance(reset["targets"], dict) or set(reset["targets"]) != set(DEFAULT_TARGETS):
        raise ValueError("A full set of initial targets is required.")
    if (reset["scenario"] == "uploaded") != ("runWindow" in reset):
        raise ValueError("Uploaded weather requires an explicit time window.")
    validate_mpc_reset(reset)
    validate_identity(recipe["identity"])
    if not isinstance(recipe["commands"], list) or not 1 <= len(recipe["commands"]) <= steps:
        raise ValueError("Invalid command sequence.")
    total = 0
    for segment in recipe["commands"]:
        if not isinstance(segment, dict) or set(segment) != {"steps", "command"}:
            raise ValueError("Invalid command segment.")
        n, command = segment["steps"], segment["command"]
        if type(n) is not int or not 1 <= n <= steps or not isinstance(command, dict):
            raise ValueError("Invalid interval count or command.")
        mode = command.get("mode")
        keys = {"mode", "targets", "controls"} if mode == "manual" else {"mode", "targets"}
        if (mode == "mpc") != (reset["mode"] == "mpc") or (
            mode == "mpc" and command.get("targets") != reset["targets"]
        ):
            raise ValueError("MPC ownership and targets must match the archived reset.")
        if mode not in ("auto", "manual", "schedule", "mpc") or set(command) != keys:
            raise ValueError("Unsupported control command.")
        if not isinstance(command["targets"], dict) or set(command["targets"]) != set(
            DEFAULT_TARGETS
        ):
            raise ValueError("Each command needs the full effective target set.")
        if mode == "schedule" and "schedule" not in reset:
            raise ValueError("Scheduled control requires a saved schedule.")
        total += n
    if total != steps:
        raise ValueError("Command intervals do not cover the exported run.")


def read_bundle(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if sorted(archive.namelist()) != sorted((RECIPE_FILE, SERIES_FILE)):
            raise ValueError("Expected settings.json and timeseries.csv exactly once.")
        for name, limit in ((RECIPE_FILE, 6 * MIB), (SERIES_FILE, 24 * MIB)):
            info = archive.getinfo(name)
            if info.file_size > limit or info.flag_bits & 1:
                raise ValueError("Oversized or encrypted archive member.")
        recipe = json.loads(archive.read(RECIPE_FILE))
        validate_recipe(recipe)
        series = archive.read(SERIES_FILE)
    if hashlib.sha256(series).hexdigest() != recipe["seriesSha256"]:
        raise ValueError("CSV checksum mismatch; the export is damaged or was edited.")
    if series.count(b"\n") != recipe["completedSteps"] + 2:
        raise ValueError("CSV does not cover the recorded endpoints.")
    return recipe


def replay(recipe, workbook=None, *, source_checkout=None):
    """Use a fresh isolated engine; never touch a running dashboard."""
    validate_recipe(recipe)
    if os.environ.get("GREENLIGHT_GYM_PATH"):
        raise ValueError(
            "Unset GREENLIGHT_GYM_PATH before replay; source overrides are not inherited."
        )
    is_checkout = recipe["identity"]["modelVersion"].startswith("gl-gym2@source-checkout+")
    if is_checkout != (source_checkout is not None):
        raise ValueError("Use --source-checkout only and explicitly for a source-checkout archive.")
    reset = dict(recipe["reset"])
    needs_weather = reset["scenario"] == "uploaded"
    if needs_weather != (workbook is not None):
        raise ValueError(
            "Supply the matching weather workbook only when replaying uploaded weather."
        )
    records = None
    if needs_weather:
        inspected = validate_weather_workbook(workbook, include_records=True)
        records = inspected.get("_records")
        if inspected.get("schemaVersion") != "amsterdam-weather-xlsx-v2" or not records:
            raise ValueError("Use the original Amsterdam-format weather workbook.")
    from backend.greenlight_adapter import GreenLightGymAdapter

    app = SimulatorApplication(
        GreenLightGymAdapter(source_path=source_checkout), requested_engine="greenlight2"
    )
    try:
        if records:
            reset["weatherId"] = app.stage_weather(records)["weatherId"]
        snapshot = app.reset(reset)["snapshot"]
        expected, actual = recipe["identity"], app.engine.archive.identity
        differences = sorted(
            k for k in set(expected) | set(actual) if expected.get(k) != actual.get(k)
        )
        if differences:
            raise ValueError("Cannot replay: different " + ", ".join(differences))
        for segment in recipe["commands"]:
            remaining = segment["steps"]
            while remaining:
                count = 1 if segment["command"]["mode"] == "mpc" else min(192, remaining)
                previous = snapshot["modelStep"]
                snapshot = app.step({**segment["command"], "steps": count})["snapshot"]
                if snapshot["modelStep"] != previous + count:
                    raise ValueError("Model stopped before the archived endpoint.")
                remaining -= count
        bundle = app.engine.archive.bundle()
        new_recipe = read_bundle(bundle)
        if recipe["format"] == FORMAT and recipe["calendar"] != new_recipe["calendar"]:
            raise ValueError("The source calendar does not match the archived run.")
        if new_recipe["seriesSha256"] != recipe["seriesSha256"]:
            raise ValueError(
                "The inputs match but the time series differs numerically; exact reproduction was not established."
            )
        return snapshot, bundle
    finally:
        app.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bundle", type=Path, help="Dashboard ZIP, used in memory without extracting it."
    )
    parser.add_argument("--weather", type=Path, help="Original .xlsx for an uploaded scenario.")
    parser.add_argument(
        "--source-checkout",
        type=Path,
        help="Explicit trusted upstream source for a checkout archive only.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write a NEW verified ZIP inside the simulator folder; do not overwrite an existing file.",
    )
    args = parser.parse_args(argv)
    try:
        output = project_destination(args.output) if args.output else None
        recipe = read_bundle(read_bounded(args.bundle, 32 * MIB))
        weather = read_bounded(args.weather, MAX_UPLOAD_BYTES) if args.weather is not None else None
        snapshot, new_bundle = replay(recipe, weather, source_checkout=args.source_checkout)
        if output:
            with project_destination(output).open("xb") as handle:
                handle.write(new_bundle)
    except (
        ApiError,
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
        KeyError,
        zipfile.BadZipFile,
    ) as exc:
        parser.exit(1, f"Replay not verified: {exc}\n")
    print(f"Verified {snapshot['modelStep']} physical steps. CSV SHA-256: {recipe['seriesSha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
