from __future__ import annotations

import argparse
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import unquote, urlsplit

from .application import ApiError as ApiError
from .application import SimulatorApplication as SimulatorApplication
from .greenlight_adapter import (
    GreenLightGymAdapter,
)
from .weather_upload import (
    MAX_UPLOAD_BYTES,
    XLSX_MIME,
    WeatherValidationError,
    validate_weather_workbook,
)

STATIC_ROOT = Path(__file__).resolve().parents[1]
MAX_BODY_BYTES = 128 * 1024
_AUTO_ENGINE = object()


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
            try:
                self._send_json(200, self.server.application.status())
            except ApiError as exc:
                self._send_json(exc.status, exc.payload(self.server.application.revision))
            except Exception:
                self._send_error(
                    503,
                    "MODEL_ERROR",
                    "GreenLight state is unavailable. Reset the model to recover.",
                )
            return
        if path.startswith("/api/"):
            self._send_error(404, "NOT_FOUND", "unknown API endpoint")
            return
        super().do_GET()

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if path == "/api/weather/preview":
            self._preview_weather()
            return
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

    def _preview_weather(self) -> None:
        # Custom header + no CORS blocks cross-site form/fetch uploads. Also verify
        # the browser Origin when present. No uploaded workbook is persisted.
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin")
        allowed_hosts = {
            f"127.0.0.1:{self.server.server_port}",
            f"localhost:{self.server.server_port}",
        }
        if (
            host not in allowed_hosts
            or (origin is not None and origin != f"http://{host}")
            or self.headers.get("X-GreenLight-Upload") != "1"
        ):
            self._send_error(403, "UPLOAD_ORIGIN", "Upload from the local simulator page.")
            return
        if not self.server.application.upload_slot.acquire(blocking=False):
            self._send_error(
                429,
                "UPLOAD_BUSY",
                "Another workbook is being checked. Try again shortly.",
            )
            return
        try:
            if self.headers.get_content_type() != XLSX_MIME:
                raise ApiError(415, "UNSUPPORTED_MEDIA_TYPE", "Upload a standard .xlsx workbook.")
            if self.headers.get("Transfer-Encoding"):
                raise ApiError(400, "INVALID_REQUEST", "Chunked uploads are not supported.")
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                raise ApiError(411, "LENGTH_REQUIRED", "Content-Length is required")
            try:
                length = int(raw_length)
            except ValueError as exc:
                raise ApiError(400, "INVALID_REQUEST", "Invalid Content-Length") from exc
            if not 0 < length <= MAX_UPLOAD_BYTES:
                raise ApiError(
                    413,
                    "PAYLOAD_TOO_LARGE",
                    "Choose a nonempty .xlsx file no larger than 2 MiB.",
                )
            self.connection.settimeout(10)
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ApiError(400, "INCOMPLETE_UPLOAD", "The workbook upload was incomplete.")
            result = validate_weather_workbook(raw, include_records=True)
            records = result.pop("_records", None)
            if (
                result.get("schemaVersion") == "amsterdam-weather-xlsx-v2"
                and records
                and self.server.application.engine is not None
            ):
                try:
                    staged = self.server.application.stage_weather(records)
                except (ApiError, ValueError) as exc:
                    result["warnings"].append(f"GreenLight run is not ready: {exc}")
                else:
                    result.update(
                        {
                            "conversionReady": True,
                            "modelReady": False,
                            "simulationReady": False,
                            "weatherId": staged["weatherId"],
                            "modelCoverageDays": staged["seasonLengthDays"],
                            "modelRowCount": staged["modelRowCount"],
                            "coverage": staged["coverage"],
                        }
                    )
                    result["warnings"] = [
                        "Weather conversion is ready in memory. Select Use this weather to initialize the full GreenLight 2 model.",
                        "The model uses the uploaded CO2 concentration, estimates soil temperature with soilTempNl(time), and retains the undocumented ?? column without consuming it.",
                    ]
            self._send_json(200, {"ok": True, "weather": result})
        except WeatherValidationError as exc:
            self._send_json(
                422,
                {
                    "ok": False,
                    "error": {
                        "code": "INVALID_WEATHER",
                        "message": str(exc),
                        "issues": exc.issues,
                    },
                },
            )
        except ApiError as exc:
            self._send_json(exc.status, exc.payload(self.server.application.revision))
        except TimeoutError:
            self._send_error(408, "UPLOAD_TIMEOUT", "Workbook upload timed out.")
        finally:
            self.server.application.upload_slot.release()

    def send_head(self):
        # SimpleHTTPRequestHandler otherwise exposes .git, .venv and future user
        # datasets. Only intentionally public assets/docs can be served, for both
        # GET and HEAD. Directory listing and escaping symlinks are never allowed.
        path = unquote(urlsplit(self.path).path)
        if path == "/":
            # Check the actual index, not just its parent directory. Never let
            # the superclass select an unchecked index file or directory list.
            path = "/index.html"
            self.path = path
        public = {
            "/frontend/charts.js",
            "/frontend/translations.js",
            "/index.html",
            "/frontend/app.js",
            "/styles.css",
            "/frontend/legacy/simulator-engine.js",
            "/frontend/climate-upload.js",
            "/frontend/run-window.js",
            "/frontend/greenhouse-settings.js",
            "/README.md",
            "/MODEL_CARD.md",
            "/PRODUCT_STRATEGY.md",
            "/GREENHOUSE_CONFIGURATION.md",
        }
        worklog = path.startswith("/worklogs/") and path.count("/") == 2 and path.endswith(".html")
        template = path == "/templates/greenlight-weather-template.xlsx"
        resolved = Path(self.translate_path(path)).resolve()
        if (
            (path not in public and not worklog and not template)
            or not resolved.is_relative_to(STATIC_ROOT)
            or not resolved.is_file()
        ):
            self.send_error(404, "Not found")
            return None
        return super().send_head()

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
            raise ApiError(
                400, "INVALID_JSON", "request body must contain valid UTF-8 JSON"
            ) from exc
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
        default="glgym",
        choices=("auto", "glgym", "browser"),
        help="require GL-Gym2 (default), auto-detect it, or serve the UI only; no approximation fallback",
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
