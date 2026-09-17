"""Application operations and revision checks, independent of HTTP transport."""

from __future__ import annotations

import threading
import uuid
from typing import Any, Mapping

from .greenhouse_config import validate_config
from .greenlight_adapter import PreservedRunResetError
from .model_defaults import CONTROL_NAMES, DEFAULT_TARGETS, SCENARIOS
from .run_window import coverage, validate_window


class ApiError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.field = field

    def payload(self, revision: int) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.field is not None:
            error["field"] = self.field
        return {"ok": False, "revision": revision, "error": error}


class SimulatorApplication:
    def __init__(
        self,
        engine: Any | None,
        *,
        requested_engine: str,
        unavailable_reason: str | None = None,
    ) -> None:
        self.engine = engine
        self.requested_engine = requested_engine
        self.unavailable_reason = unavailable_reason
        self.revision = 0
        self.lock = threading.RLock()
        self.upload_slot = threading.BoundedSemaphore(1)
        self.model_error: str | None = None
        self.uploaded_weather: dict[str, dict[str, Any]] = {}
        self.active_weather_id: str | None = None
        self.active_run_window: dict[str, Any] | None = None
        self.pending_weather_id: str | None = None

    def close(self) -> None:
        self.uploaded_weather.clear()
        self.active_weather_id = None
        self.active_run_window = None
        self.pending_weather_id = None
        if self.engine is not None and hasattr(self.engine, "close"):
            self.engine.close()

    def stage_weather(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """Validate model conversion and retain active plus pending datasets."""
        with self.lock:
            self._require_engine()
            if self.model_error:
                raise ApiError(503, "MODEL_ERROR", self.model_error)
            prepared = self.engine.prepare_uploaded_weather(records)
            weather_id = uuid.uuid4().hex
            self.uploaded_weather[weather_id] = {
                "prepared": prepared,
                "label": "Uploaded weather",
                "coverage": coverage(int(records[0]["time"]), int(records[-1]["time"])),
            }
            self.pending_weather_id = weather_id
            retained = {weather_id, self.active_weather_id}
            self.uploaded_weather = {
                key: value for key, value in self.uploaded_weather.items() if key in retained
            }
            return {
                "weatherId": weather_id,
                "seasonLengthDays": int(prepared["seasonLengthDays"]),
                "modelRowCount": int(prepared["modelRowCount"]),
                "coverage": self.uploaded_weather[weather_id]["coverage"],
            }

    def _get_staged_weather(self, weather_id: Any) -> dict[str, Any]:
        if (
            not isinstance(weather_id, str)
            or not weather_id.isalnum()
            or not 16 <= len(weather_id) <= 80
        ):
            raise ApiError(400, "INVALID_REQUEST", "weatherId is invalid", "weatherId")
        try:
            return self.uploaded_weather[weather_id]
        except KeyError as exc:
            raise ApiError(
                410,
                "WEATHER_EXPIRED",
                "Upload the weather workbook again.",
                "weatherId",
            ) from exc

    def status(self) -> dict[str, Any]:
        with self.lock:
            if self.model_error:
                raise ApiError(503, "MODEL_ERROR", self.model_error)
            metadata = (
                self.engine.metadata()
                if self.engine is not None
                else {
                    "active": "unavailable",
                    "scientific": False,
                    "model": "GreenLight scientific model unavailable",
                    "stepMinutes": 15,
                    "fallbackReason": self.unavailable_reason,
                }
            )
            return {
                "ok": True,
                "apiVersion": 1,
                "revision": self.revision,
                "realModelAvailable": self.engine is not None,
                "engine": {
                    "requested": self.requested_engine,
                    **metadata,
                },
                "snapshot": self.engine.snapshot() if self.engine is not None else None,
            }

    def reset(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        allowed = {
            "seed",
            "scenario",
            "mode",
            "targets",
            "expectedRevision",
            "weatherId",
            "runWindow",
            "greenhouseConfig",
        }
        self._reject_unknown(payload, allowed)
        self._validate_reset(payload)
        with self.lock:
            self._require_engine()
            self._check_revision(payload)
            engine_payload = dict(payload)
            weather_id = payload.get("weatherId")
            scenario = payload.get("scenario")
            if scenario is None and self.active_weather_id:
                scenario = "uploaded"
                weather_id = self.active_weather_id
                engine_payload.update(
                    scenario=scenario,
                    weatherId=weather_id,
                    runWindow=dict(self.active_run_window),
                )
            if scenario == "uploaded":
                staged = self._get_staged_weather(weather_id)
                try:
                    validate_window(engine_payload.get("runWindow"), staged["coverage"])
                except ValueError as exc:
                    raise ApiError(400, "INVALID_WINDOW", str(exc), "runWindow") from exc
                engine_payload.update(
                    {
                        "_prepared_weather": staged["prepared"],
                        "_weather_id": weather_id,
                        "_weather_label": staged["label"],
                    }
                )
            try:
                snapshot = self.engine.reset(engine_payload)
            except PreservedRunResetError as exc:
                # The adapter certifies rollback; keep revision, active data and access.
                raise ApiError(422, "RESET_REJECTED", str(exc)) from exc
            except ValueError as exc:
                raise ApiError(400, "INVALID_REQUEST", str(exc)) from exc
            except Exception as exc:
                self.model_error = "GreenLight reset failed. Reset the model to recover."
                self.revision += 1
                raise ApiError(500, "MODEL_ERROR", f"GreenLight reset failed: {exc}") from exc
            self.model_error = None
            self.active_weather_id = weather_id if scenario == "uploaded" else None
            self.active_run_window = (
                dict(engine_payload["runWindow"]) if scenario == "uploaded" else None
            )
            if self.active_weather_id == self.pending_weather_id:
                self.pending_weather_id = None
            self.revision += 1
            return self._success(snapshot)

    def step(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        allowed = {"steps", "mode", "controls", "targets", "expectedRevision"}
        self._reject_unknown(payload, allowed)
        self._validate_step(payload)
        with self.lock:
            self._require_engine()
            self._check_revision(payload)
            if self.model_error:
                raise ApiError(503, "MODEL_ERROR", self.model_error)
            try:
                snapshot = self.engine.step(payload)
            except ValueError as exc:
                raise ApiError(400, "INVALID_REQUEST", str(exc)) from exc
            except Exception as exc:
                self.model_error = "GreenLight integration failed. Reset the model to recover."
                self.revision += 1
                raise ApiError(500, "MODEL_ERROR", f"GreenLight step failed: {exc}") from exc
            self.revision += 1
            return self._success(snapshot)

    def _success(self, snapshot: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "ok": True,
            "apiVersion": 1,
            "revision": self.revision,
            "engine": self.engine.metadata(),
            "snapshot": snapshot,
        }

    def _require_engine(self) -> None:
        if self.engine is None:
            raise ApiError(
                503,
                "MODEL_UNAVAILABLE",
                self.unavailable_reason or "GreenLight-Gym2 is not available",
            )

    def _check_revision(self, payload: Mapping[str, Any]) -> None:
        if "expectedRevision" not in payload:
            return
        expected = payload["expectedRevision"]
        if isinstance(expected, bool) or not isinstance(expected, int):
            raise ApiError(
                400,
                "INVALID_REQUEST",
                "expectedRevision must be an integer",
                "expectedRevision",
            )
        if expected != self.revision:
            raise ApiError(
                409,
                "STALE_REVISION",
                f"expected revision {expected}, current revision is {self.revision}",
                "expectedRevision",
            )

    @staticmethod
    def _reject_unknown(payload: Mapping[str, Any], allowed: set[str]) -> None:
        unknown = sorted(set(payload) - allowed)
        if unknown:
            raise ApiError(
                400,
                "INVALID_REQUEST",
                f"unknown field: {unknown[0]}",
                unknown[0],
            )

    @staticmethod
    def _validate_targets(targets: Any) -> None:
        if targets is None:
            return
        if not isinstance(targets, Mapping):
            raise ApiError(400, "INVALID_REQUEST", "targets must be an object", "targets")
        unknown = sorted(set(targets) - set(DEFAULT_TARGETS))
        if unknown:
            raise ApiError(
                400,
                "INVALID_REQUEST",
                f"unknown target: {unknown[0]}",
                f"targets.{unknown[0]}",
            )
        ranges = {
            "dayTemp": (10.0, 35.0),
            "nightTemp": (8.0, 30.0),
            "co2": (300.0, 1600.0),
            "maxRh": (40.0, 98.0),
        }
        for name, value in targets.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ApiError(400, "INVALID_REQUEST", f"{name} must be numeric", f"targets.{name}")
            minimum, maximum = ranges[name]
            if not minimum <= float(value) <= maximum:
                raise ApiError(
                    400,
                    "INVALID_REQUEST",
                    f"{name} must be between {minimum:g} and {maximum:g}",
                    f"targets.{name}",
                )

    def _validate_reset(self, payload: Mapping[str, Any]) -> None:
        if "greenhouseConfig" in payload:
            try:
                validate_config(payload["greenhouseConfig"])
            except ValueError as exc:
                raise ApiError(400, "INVALID_CONFIGURATION", str(exc), "greenhouseConfig") from exc
        scenario = payload.get("scenario")
        if scenario == "uploaded" and "weatherId" not in payload:
            raise ApiError(
                400,
                "INVALID_REQUEST",
                "uploaded scenario requires weatherId",
                "weatherId",
            )
        if scenario is not None and scenario != "uploaded" and scenario not in SCENARIOS:
            raise ApiError(400, "INVALID_REQUEST", "unknown weather scenario", "scenario")
        if "weatherId" in payload and scenario != "uploaded":
            raise ApiError(
                400,
                "INVALID_REQUEST",
                "weatherId requires the uploaded scenario",
                "weatherId",
            )
        if "runWindow" in payload and scenario != "uploaded":
            raise ApiError(
                400,
                "INVALID_WINDOW",
                "runWindow requires uploaded weather",
                "runWindow",
            )
        mode = payload.get("mode")
        if mode is not None and mode not in {"auto", "manual"}:
            raise ApiError(400, "INVALID_REQUEST", "mode must be auto or manual", "mode")
        seed = payload.get("seed")
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
            raise ApiError(400, "INVALID_REQUEST", "seed must be an integer", "seed")
        self._validate_targets(payload.get("targets"))

    def _validate_step(self, payload: Mapping[str, Any]) -> None:
        steps = payload.get("steps", 1)
        if isinstance(steps, bool) or not isinstance(steps, int) or not 1 <= steps <= 192:
            raise ApiError(
                400,
                "INVALID_REQUEST",
                "steps must be an integer from 1 to 192",
                "steps",
            )
        mode = payload.get("mode")
        if mode is not None and mode not in {"auto", "manual"}:
            raise ApiError(400, "INVALID_REQUEST", "mode must be auto or manual", "mode")
        self._validate_targets(payload.get("targets"))

        controls = payload.get("controls")
        if mode == "manual" and not isinstance(controls, Mapping):
            raise ApiError(400, "INVALID_REQUEST", "manual mode requires controls", "controls")
        if controls is None:
            return
        if not isinstance(controls, Mapping):
            raise ApiError(400, "INVALID_REQUEST", "controls must be an object", "controls")
        if set(controls) != set(CONTROL_NAMES):
            raise ApiError(
                400,
                "INVALID_REQUEST",
                "controls must contain exactly the six GreenLight control names",
                "controls",
            )
        for name in CONTROL_NAMES:
            value = controls[name]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not 0 <= float(value) <= 1
            ):
                raise ApiError(
                    400,
                    "INVALID_REQUEST",
                    f"{name} must be between 0 and 1",
                    f"controls.{name}",
                )
