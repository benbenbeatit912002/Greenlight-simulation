from __future__ import annotations

import argparse
import json
import threading
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

from .greenlight_adapter import (
    CONTROL_NAMES,
    DEFAULT_TARGETS,
    SCENARIOS,
    GreenLightGymAdapter,
)


STATIC_ROOT = Path(__file__).resolve().parents[1]
MAX_BODY_BYTES = 128 * 1024
_AUTO_ENGINE = object()


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

    def close(self) -> None:
        if self.engine is not None and hasattr(self.engine, "close"):
            self.engine.close()

    def status(self) -> dict[str, Any]:
        with self.lock:
            metadata = (
                self.engine.metadata()
                if self.engine is not None
                else {
                    "active": "browser",
                    "scientific": False,
                    "model": "Browser fallback model",
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
        allowed = {"seed", "scenario", "mode", "targets", "expectedRevision"}
        self._reject_unknown(payload, allowed)
        self._validate_reset(payload)
        with self.lock:
            self._require_engine()
            self._check_revision(payload)
            try:
                snapshot = self.engine.reset(payload)
            except ValueError as exc:
                raise ApiError(400, "INVALID_REQUEST", str(exc)) from exc
            except Exception as exc:
                raise ApiError(500, "MODEL_ERROR", f"GreenLight reset failed: {exc}") from exc
            self.revision += 1
            return self._success(snapshot)

    def step(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        allowed = {"steps", "mode", "controls", "targets", "expectedRevision"}
        self._reject_unknown(payload, allowed)
        self._validate_step(payload)
        with self.lock:
            self._require_engine()
            self._check_revision(payload)
            try:
                snapshot = self.engine.step(payload)
            except ValueError as exc:
                raise ApiError(400, "INVALID_REQUEST", str(exc)) from exc
            except Exception as exc:
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
            raise ApiError(400, "INVALID_REQUEST", "expectedRevision must be an integer", "expectedRevision")
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
            raise ApiError(400, "INVALID_REQUEST", f"unknown target: {unknown[0]}", f"targets.{unknown[0]}")
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
        scenario = payload.get("scenario")
        if scenario is not None and scenario not in SCENARIOS:
            raise ApiError(400, "INVALID_REQUEST", "unknown weather scenario", "scenario")
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
            raise ApiError(400, "INVALID_REQUEST", "steps must be an integer from 1 to 192", "steps")
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
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= float(value) <= 1:
                raise ApiError(400, "INVALID_REQUEST", f"{name} must be between 0 and 1", f"controls.{name}")


class SimulatorHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address, handler, application: SimulatorApplication):
        self.application = application
        super().__init__(server_address, handler)

    def server_close(self) -> None:
        try:
            self.application.close()
        finally:
            super().server_close()


class SimulatorRequestHandler(SimpleHTTPRequestHandler):
    server_version = "GreenLightSimulator/1.0"

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        super().end_headers()

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/api/status":
            self._send_json(200, self.server.application.status())
            return
        if path.startswith("/api/"):
            self._send_error(404, "NOT_FOUND", "unknown API endpoint")
            return
        super().do_GET()

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if path not in {"/api/reset", "/api/step"}:
            self._send_error(404, "NOT_FOUND", "unknown API endpoint")
            return

        try:
            payload = self._read_json_body()
            if path == "/api/reset":
                response = self.server.application.reset(payload)
            else:
                response = self.server.application.step(payload)
            self._send_json(200, response)
        except ApiError as exc:
            self._send_json(exc.status, exc.payload(self.server.application.revision))

    def _read_json_body(self) -> Mapping[str, Any]:
        content_type = self.headers.get_content_type()
        if content_type != "application/json":
            raise ApiError(415, "UNSUPPORTED_MEDIA_TYPE", "Content-Type must be application/json")
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise ApiError(411, "LENGTH_REQUIRED", "Content-Length is required")
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ApiError(400, "INVALID_REQUEST", "invalid Content-Length") from exc
        if length < 0 or length > MAX_BODY_BYTES:
            raise ApiError(413, "PAYLOAD_TOO_LARGE", "request body is too large")
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError(400, "INVALID_JSON", "request body must contain valid UTF-8 JSON") from exc
        if not isinstance(payload, Mapping):
            raise ApiError(400, "INVALID_REQUEST", "request body must be a JSON object")
        return payload

    def _send_error(self, status: int, code: str, message: str) -> None:
        error = ApiError(status, code, message)
        self._send_json(status, error.payload(self.server.application.revision))

    def _send_json(self, status: int, payload: Mapping[str, Any]) -> None:
        try:
            body = json.dumps(
                payload,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            body = json.dumps(
                {
                    "ok": False,
                    "revision": self.server.application.revision,
                    "error": {
                        "code": "SERIALIZATION_ERROR",
                        "message": f"model returned non-JSON data: {exc}",
                    },
                },
                ensure_ascii=False,
            ).encode("utf-8")
            status = 500
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def create_server(
    host: str = "127.0.0.1",
    port: int = 4173,
    *,
    requested_engine: str = "auto",
    engine: Any = _AUTO_ENGINE,
) -> SimulatorHTTPServer:
    if requested_engine not in {"auto", "glgym", "browser"}:
        raise ValueError("requested_engine must be auto, glgym, or browser")

    unavailable_reason: str | None = None
    resolved_engine = engine
    if engine is _AUTO_ENGINE:
        resolved_engine = None
        if requested_engine != "browser":
            try:
                resolved_engine = GreenLightGymAdapter()
            except Exception as exc:
                unavailable_reason = str(exc)
                if requested_engine == "glgym":
                    raise RuntimeError(unavailable_reason) from exc
        else:
            unavailable_reason = "scientific backend disabled by --engine browser"

    application = SimulatorApplication(
        resolved_engine,
        requested_engine=requested_engine,
        unavailable_reason=unavailable_reason,
    )
    handler = partial(SimulatorRequestHandler, directory=str(STATIC_ROOT))
    return SimulatorHTTPServer((host, port), handler, application)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Serve the GreenLight 2 greenhouse simulator")
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default: loopback only)")
    parser.add_argument("--port", default=4173, type=int, help="HTTP port")
    parser.add_argument(
        "--engine",
        default="auto",
        choices=("auto", "glgym", "browser"),
        help="auto-detect GL-Gym2, require it, or use the browser model",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        server = create_server(args.host, args.port, requested_engine=args.engine)
    except RuntimeError as exc:
        print(f"Unable to start the GreenLight model: {exc}")
        return 2

    status = server.application.status()
    engine_name = status["engine"]["active"]
    print(f"GreenLight simulator: http://{args.host}:{server.server_port}/")
    print(f"Active engine: {engine_name}")
    if status["engine"].get("fallbackReason"):
        print(f"Fallback reason: {status['engine']['fallbackReason']}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping simulator")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

