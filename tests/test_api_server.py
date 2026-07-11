from __future__ import annotations

import http.client
import json
import threading
import unittest
from typing import Any, Mapping

from backend.server import create_server


class FakeEngine:
    def __init__(self) -> None:
        self.step_value = 0
        self.mode = "auto"
        self.closed = False

    def metadata(self) -> dict[str, Any]:
        return {
            "active": "fake-greenlight",
            "scientific": True,
            "stepMinutes": 15,
            "stateCount": 28,
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "modelStep": self.step_value,
            "mode": self.mode,
            "controls": {
                "uBoil": 0.5,
                "uCO2": 0.5,
                "uThScr": 0.5,
                "uVent": 0.5,
                "uLamp": 0.5,
                "uBlScr": 0.5,
            },
            "history": [],
        }

    def reset(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        self.step_value = 0
        self.mode = str(payload.get("mode", "auto"))
        return self.snapshot()

    def step(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        self.step_value += int(payload.get("steps", 1))
        self.mode = str(payload.get("mode", self.mode))
        return self.snapshot()

    def close(self) -> None:
        self.closed = True


class ApiServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = FakeEngine()
        cls.server = create_server(port=0, engine=cls.engine)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
        *,
        raw_body: bytes | None = None,
        content_type: str = "application/json",
    ) -> tuple[int, dict[str, Any] | str, Mapping[str, str]]:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        headers: dict[str, str] = {}
        body = raw_body
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        if body is not None:
            headers["Content-Type"] = content_type
            headers["Content-Length"] = str(len(body))
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        data = response.read()
        response_headers = {name.lower(): value for name, value in response.getheaders()}
        connection.close()
        if response_headers.get("content-type", "").startswith("application/json"):
            return response.status, json.loads(data), response_headers
        return response.status, data.decode("utf-8"), response_headers

    def test_static_index_is_served(self) -> None:
        status, body, headers = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("GreenLight 2", body)
        self.assertTrue(headers["content-type"].startswith("text/html"))

    def test_status_reports_scientific_engine(self) -> None:
        status, body, headers = self.request("GET", "/api/status")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertTrue(body["realModelAvailable"])
        self.assertEqual(body["engine"]["active"], "fake-greenlight")
        self.assertEqual(headers["cache-control"], "no-store")

    def test_reset_then_step_uses_revision(self) -> None:
        _, status_body, _ = self.request("GET", "/api/status")
        revision = status_body["revision"]
        reset_status, reset_body, _ = self.request(
            "POST",
            "/api/reset",
            {
                "seed": 42,
                "scenario": "spring",
                "mode": "manual",
                "targets": {"dayTemp": 21.5},
                "expectedRevision": revision,
            },
        )
        self.assertEqual(reset_status, 200)
        self.assertEqual(reset_body["snapshot"]["modelStep"], 0)

        controls = {
            "uBoil": 0.1,
            "uCO2": 0.2,
            "uThScr": 0.3,
            "uVent": 0.4,
            "uLamp": 0.5,
            "uBlScr": 0.6,
        }
        step_status, step_body, _ = self.request(
            "POST",
            "/api/step",
            {
                "steps": 4,
                "mode": "manual",
                "controls": controls,
                "expectedRevision": reset_body["revision"],
            },
        )
        self.assertEqual(step_status, 200)
        self.assertEqual(step_body["snapshot"]["modelStep"], 4)
        self.assertEqual(step_body["revision"], reset_body["revision"] + 1)

    def test_stale_revision_is_rejected(self) -> None:
        status, body, _ = self.request(
            "POST",
            "/api/reset",
            {"expectedRevision": -1},
        )
        self.assertEqual(status, 409)
        self.assertEqual(body["error"]["code"], "STALE_REVISION")

    def test_invalid_manual_controls_are_rejected(self) -> None:
        status, body, _ = self.request(
            "POST",
            "/api/step",
            {
                "steps": 1,
                "mode": "manual",
                "controls": {"uBoil": 2},
            },
        )
        self.assertEqual(status, 400)
        self.assertEqual(body["error"]["field"], "controls")

    def test_invalid_json_is_rejected(self) -> None:
        status, body, _ = self.request(
            "POST",
            "/api/reset",
            raw_body=b"{bad-json",
        )
        self.assertEqual(status, 400)
        self.assertEqual(body["error"]["code"], "INVALID_JSON")


class UnavailableEngineTests(unittest.TestCase):
    def test_browser_only_server_returns_503_for_model_mutation(self) -> None:
        server = create_server(port=0, requested_engine="browser", engine=None)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            body = b"{}"
            connection.request(
                "POST",
                "/api/reset",
                body=body,
                headers={"Content-Type": "application/json", "Content-Length": str(len(body))},
            )
            response = connection.getresponse()
            payload = json.loads(response.read())
            connection.close()
            self.assertEqual(response.status, 503)
            self.assertEqual(payload["error"]["code"], "MODEL_UNAVAILABLE")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
