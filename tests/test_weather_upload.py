from __future__ import annotations

import hashlib
import http.client
import json
import threading
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

from weather_fixtures import workbook_bytes

from backend.server import create_server
from backend.weather_upload import (
    COLUMNS,
    MAX_UPLOAD_BYTES,
    XLSX_MIME,
    WeatherValidationError,
    validate_weather_workbook,
)

DEFAULT_WINDOW = {
    "sourceYear": 2010,
    "timeConvention": "source-local-standard",
    "startSeconds": 0,
    "endSeconds": 86400,
}


class StagingEngine:
    def __init__(self):
        self.reset_payload = None

    def metadata(self):
        return {"active": "greenlight-gym2", "scientific": True}

    def snapshot(self):
        return {
            "engine": "greenlight-gym2",
            "modelReady": True,
            "runId": "fake-run",
            "scenario": "spring",
        }

    def prepare_uploaded_weather(self, records):
        self.records = records
        return {
            "weather": [[0.0] * 10] * 145,
            "seasonLengthDays": 1,
            "modelRowCount": 145,
        }

    def reset(self, payload):
        self.reset_payload = payload
        return {
            "engine": "greenlight-gym2",
            "runId": "new-run",
            "scenario": payload["scenario"],
        }

    def close(self):
        pass


def rewrite_workbook(transform):
    with ZipFile(BytesIO(workbook_bytes())) as source:
        entries = {name: source.read(name).decode() for name in source.namelist()}
    transform(entries)
    result = BytesIO()
    with ZipFile(result, "w", ZIP_DEFLATED) as archive:
        for name, contents in entries.items():
            archive.writestr(name, contents)
    return result.getvalue()


class WorkbookValidationTests(unittest.TestCase):
    def assert_invalid(self, raw, code=None):
        with self.assertRaises(WeatherValidationError) as ctx:
            validate_weather_workbook(raw)
        if code:
            self.assertIn(code, [issue["code"] for issue in ctx.exception.issues])
        return ctx.exception.issues

    def test_preview_and_fingerprint_no_model_or_storage(self):
        raw = workbook_bytes()
        with patch("pathlib.Path.write_bytes", side_effect=AssertionError("must not save")):
            result = validate_weather_workbook(raw)
        self.assertEqual(result["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["rowCount"], 2)
        self.assertEqual(result["intervalMinutes"], 15)
        self.assertEqual(result["durationHours"], 0.25)
        self.assertEqual(result["ranges"]["outside_temperature_C"], {"min": 10, "max": 11})
        self.assertEqual(result["missingModelColumns"], list(COLUMNS[5:]))
        self.assertFalse(result["simulationReady"])
        self.assertFalse(result["stored"])

    def test_explicit_offsets_are_normalized(self):
        rows = [
            ["2026-01-01T01:00:00+01:00", 10, 80, 0, 2],
            ["2026-01-01T01:15:00+01:00", 10, 80, 0, 2],
        ]
        self.assertEqual(
            validate_weather_workbook(workbook_bytes(rows))["start"],
            "2026-01-01T00:00:00Z",
        )

    def test_forged_dimension_does_not_hide_data(self):
        self.assertEqual(
            validate_weather_workbook(workbook_bytes(dimension="A1:A1"))["rowCount"], 2
        )

    def test_invalid_values_report_excel_row_and_column(self):
        rows = [
            ["2026-01-01T00:00:00Z", 10, 101, 0, 2],
            ["2026-01-01T00:15:00Z", "10", 80, 0, True],
        ]
        issues = self.assert_invalid(workbook_bytes(rows), "RANGE")
        self.assertEqual(issues[0]["row"], 2)
        self.assertEqual(issues[0]["column"], "outside_relative_humidity_pct")
        self.assertEqual(len(issues), 3)

    def test_formulas_rejected_even_with_cached_values(self):
        self.assert_invalid(
            workbook_bytes([["2026-01-01T00:00:00Z", ("1+9",), 80, 0, 2]]), "FORMULA"
        )

    def test_missing_timezone_rejected(self):
        self.assert_invalid(workbook_bytes([["2026-01-01T00:00:00", 10, 80, 0, 2]]), "TIMESTAMP")

    def test_duplicate_and_irregular_time_rejected(self):
        for moment, code in [("00:00", "ORDER"), ("00:45", "INTERVAL")]:
            rows = [
                ["2026-01-01T00:00:00Z", 10, 80, 0, 2],
                [f"2026-01-01T{moment}:00Z", 10, 80, 0, 2],
                ["2026-01-01T01:00:00Z", 10, 80, 0, 2],
            ]
            self.assert_invalid(workbook_bytes(rows), code)

    def test_partial_optional_column_rejected(self):
        rows = [
            ["2026-01-01T00:00:00Z", 10, 80, 0, 2, 5, None, None],
            ["2026-01-01T00:15:00Z", 10, 80, 0, 2, None, None, None],
        ]
        self.assert_invalid(workbook_bytes(rows, COLUMNS), "PARTIAL_COLUMN")

    def test_complete_columns_do_not_claim_simulation_readiness(self):
        rows = [[f"2026-01-01T00:{minute:02}:00Z", 10, 80, 0, 2, 5, 10, 420] for minute in (0, 15)]
        result = validate_weather_workbook(workbook_bytes(rows, COLUMNS))
        self.assertEqual(result["missingModelColumns"], [])
        self.assertFalse(result["simulationReady"])

    def test_unknown_or_duplicate_headers_rejected(self):
        self.assert_invalid(workbook_bytes(headers=("time", *COLUMNS[1:5])), "HEADERS")
        self.assert_invalid(
            workbook_bytes(headers=("timestamp_utc", "timestamp_utc", *COLUMNS[2:5])),
            "HEADERS",
        )

    def test_blank_middle_row_and_extra_data_rejected(self):
        rows = [
            ["2026-01-01T00:00:00Z", 10, 80, 0, 2],
            [],
            ["2026-01-01T00:15:00Z", 10, 80, 0, 2, 7],
        ]
        self.assert_invalid(workbook_bytes(rows), "EMPTY_ROW")

    def test_hostile_or_damaged_archives_rejected(self):
        for raw in [
            b"not excel",
            b"",
            b"0" * (MAX_UPLOAD_BYTES + 1),
            workbook_bytes(extra_entries={"xl/vbaProject.bin": b"macro"}),
            workbook_bytes(extra_entries={"../escape.xml": "<a/>"}),
            workbook_bytes(extra_entries={"xl/externalLinks/link.xml": "<a/>"}),
            workbook_bytes(
                extra_entries={"evil.xml": '<!DOCTYPE x [<!ENTITY x "boom">]><x>&x;</x>'}
            ),
        ]:
            with self.subTest(size=len(raw)):
                self.assert_invalid(raw)

    def test_excessive_decompression_rejected(self):
        self.assert_invalid(
            workbook_bytes(extra_entries={"large.txt": "x" * (17 * 1024 * 1024)}),
            "FILE_SIZE",
        )

    def test_fragmented_strings_and_timestamp_errors_are_bounded(self):
        def fragment(entries):
            key = "xl/worksheets/sheet1.xml"
            fragments = "<r><t>" + "x" * 1024 + "</t></r>"
            entries[key] = entries[key].replace(
                "<is><t>2026-01-01T00:00:00Z</t></is>",
                "<is>" + fragments * 500 + "</is>",
            )

        issues = self.assert_invalid(rewrite_workbook(fragment), "CELL_SIZE")
        self.assertLess(len(json.dumps(issues)), 500)

        def shared(entries):
            fragments = ("<r><t>" + "x" * 1024 + "</t></r>") * 500
            entries["xl/sharedStrings.xml"] = (
                '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si>'
                + fragments
                + "</si></sst>"
            )

        self.assert_invalid(rewrite_workbook(shared), "CELL_SIZE")
        issues = self.assert_invalid(workbook_bytes([["x" * 4000, 10, 80, 0, 2]]), "TIMESTAMP")
        self.assertLess(len(json.dumps(issues)), 500)

    def test_nonstandard_worksheet_part_and_row_indices_checked(self):
        def move(entries):
            entries["xl/data.xml"] = entries.pop("xl/worksheets/sheet1.xml").replace(
                '<row r="3">', '<row r="10003">'
            )
            entries["xl/_rels/workbook.xml.rels"] = entries["xl/_rels/workbook.xml.rels"].replace(
                "worksheets/sheet1.xml", "data.xml"
            )
            entries["[Content_Types].xml"] = entries["[Content_Types].xml"].replace(
                "worksheets/sheet1.xml", "data.xml"
            )

        self.assert_invalid(rewrite_workbook(move), "SHEET_SIZE")
        for suffix in ("XML", "data"):

            def hidden_part(entries):
                move(entries)
                destination = f"data.{suffix}"
                entries[f"xl/{destination}"] = entries.pop("xl/data.xml")
                for name in ("xl/_rels/workbook.xml.rels", "[Content_Types].xml"):
                    entries[name] = entries[name].replace("data.xml", destination)

            with self.subTest(suffix=suffix):
                self.assert_invalid(rewrite_workbook(hidden_part))

        def mismatch(entries):
            key = "xl/worksheets/sheet1.xml"
            entries[key] = entries[key].replace('<row r="3">', '<row r="4">')

        self.assert_invalid(rewrite_workbook(mismatch), "CELL_COORDINATE")

    def test_duplicate_cell_cannot_hide_an_invalid_value(self):
        def duplicate(entries):
            key = "xl/worksheets/sheet1.xml"
            entries[key] = entries[key].replace(
                '<c r="B2" t="n"><v>10</v></c>',
                '<c r="B2" t="n"><v>9999</v></c><c r="B2" t="n"><v>10</v></c>',
            )

        self.assert_invalid(rewrite_workbook(duplicate), "DUPLICATE_CELL")

    def test_published_template_matches_amsterdam_seconds(self):
        raw = (
            Path(__file__).resolve().parents[1] / "templates" / "greenlight-weather-template.xlsx"
        ).read_bytes()
        result = validate_weather_workbook(raw)
        self.assertEqual(result["rowCount"], 433)
        self.assertEqual(result["schemaVersion"], "amsterdam-weather-xlsx-v2")
        self.assertEqual(result["intervalMinutes"], 5)
        self.assertEqual(result["durationHours"], 36)
        self.assertFalse(result["simulationReady"])


class WeatherApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(port=0, requested_engine="browser", engine=None)
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(2)

    def request(self, method="POST", path="/api/weather/preview", raw=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        request_headers = {"Content-Type": XLSX_MIME, "X-GreenLight-Upload": "1"}
        request_headers.update(headers or {})
        connection.request(
            method,
            path,
            body=workbook_bytes() if raw is None and method == "POST" else raw,
            headers=request_headers,
        )
        response = connection.getresponse()
        body = response.read()
        result = (
            json.loads(body)
            if response.getheader("Content-Type", "").startswith("application/json")
            else body
        )
        status = response.status
        connection.close()
        return status, result

    def test_upload_without_model_and_revision_unchanged(self):
        revision = self.server.application.revision
        status, body = self.request()
        self.assertEqual(status, 200)
        self.assertFalse(body["weather"]["stored"])
        self.assertEqual(self.server.application.revision, revision)
        self.assertIsNone(self.server.application.engine)

    def test_invalid_workbook_has_structured_errors(self):
        status, body = self.request(raw=b"invalid")
        self.assertEqual(status, 422)
        self.assertIn("issues", body["error"])

    def test_origin_mime_and_request_size_are_enforced(self):
        for headers, expected in [
            ({"Origin": "https://example.com"}, 403),
            ({"X-GreenLight-Upload": "0"}, 403),
            ({"Host": "attacker.example"}, 403),
            ({"Content-Type": "text/plain"}, 415),
            ({"Content-Length": str(MAX_UPLOAD_BYTES + 1)}, 413),
        ]:
            with self.subTest(headers=headers):
                self.assertEqual(self.request(headers=headers)[0], expected)

    def test_parallel_upload_rejected_without_changing_model(self):
        self.server.application.upload_slot.acquire()
        try:
            self.assertEqual(self.request()[0], 429)
        finally:
            self.server.application.upload_slot.release()

    def test_private_files_and_directory_listings_not_served(self):
        for method in ("GET", "HEAD"):
            for path in (
                "/.git/config",
                "/.venv/pyvenv.cfg",
                "/.runtime/",
                "/user_data/private.xlsx",
                "/backend/server.py",
                "/worklogs/",
                "/%2e%2e/.git/config",
            ):
                with self.subTest(method=method, path=path):
                    self.assertEqual(self.request(method=method, path=path)[0], 404)

    def test_template_download(self):
        status, body = self.request(
            method="GET", path="/templates/greenlight-weather-template.xlsx"
        )
        self.assertEqual(status, 200)
        self.assertEqual(validate_weather_workbook(body)["rowCount"], 433)

    def test_root_checks_the_selected_index_containment(self):
        from backend.server import STATIC_ROOT

        real_resolve = Path.resolve

        def fake_escape(candidate, *args, **kwargs):
            if candidate == STATIC_ROOT / "index.html":
                # Simulate an escaping symlink without creating or reading one.
                return STATIC_ROOT.parent / "outside-index.html"
            return real_resolve(candidate, *args, **kwargs)

        with patch.object(Path, "resolve", fake_escape):
            for method in ("GET", "HEAD"):
                for route in ("/", "/index.html"):
                    self.assertEqual(self.request(method=method, path=route)[0], 404)


class StagedWeatherApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = StagingEngine()
        cls.server = create_server(port=0, requested_engine="glgym", engine=cls.engine)
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(2)

    def request(self, path, body, headers):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=10)
        connection.request("POST", path, body=body, headers=headers)
        response = connection.getresponse()
        result = json.loads(response.read())
        status = response.status
        connection.close()
        return status, result

    def test_upload_stages_in_memory_and_reset_requires_explicit_id(self):
        rows = [
            [index * 300, 100, 2, 12, 5, 0, 450, index * 300 / 86400, 75] for index in range(433)
        ]
        status, body = self.request(
            "/api/weather/preview",
            workbook_bytes(
                rows,
                headers=(
                    "time",
                    "global radiation",
                    "wind speed",
                    "air temperature",
                    "sky temperature",
                    "??",
                    "CO2 concentration",
                    "day number",
                    "RH",
                ),
            ),
            {"Content-Type": XLSX_MIME, "X-GreenLight-Upload": "1"},
        )
        self.assertEqual(status, 200)
        weather = body["weather"]
        self.assertTrue(weather["conversionReady"])
        self.assertFalse(weather["modelReady"])
        self.assertFalse(weather["simulationReady"])
        self.assertFalse(weather["stored"])
        self.assertRegex(weather["weatherId"], r"^[0-9a-f]{32}$")
        self.assertEqual(self.server.application.revision, 0)

        for invalid_window in (None, {**DEFAULT_WINDOW, "endSeconds": 87300}):
            invalid_status, invalid_body = self.request(
                "/api/reset",
                json.dumps(
                    {
                        "scenario": "uploaded",
                        "weatherId": weather["weatherId"],
                        "runWindow": invalid_window,
                        "expectedRevision": 0,
                    }
                ).encode(),
                {"Content-Type": "application/json"},
            )
            self.assertEqual(invalid_status, 400)
            self.assertEqual(invalid_body["error"]["code"], "INVALID_WINDOW")
            self.assertEqual(self.server.application.revision, 0)
            self.assertIsNone(self.engine.reset_payload)

        status, response = self.request(
            "/api/reset",
            json.dumps(
                {
                    "scenario": "uploaded",
                    "weatherId": weather["weatherId"],
                    "runWindow": DEFAULT_WINDOW,
                    "expectedRevision": 0,
                }
            ).encode(),
            {"Content-Type": "application/json"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(self.engine.reset_payload["scenario"], "uploaded")
        self.assertIn("_prepared_weather", self.engine.reset_payload)
        self.assertEqual(response["snapshot"]["scenario"], "uploaded")

        second_status, second_body = self.request(
            "/api/weather/preview",
            workbook_bytes(
                rows,
                headers=(
                    "time",
                    "global radiation",
                    "wind speed",
                    "air temperature",
                    "sky temperature",
                    "??",
                    "CO2 concentration",
                    "day number",
                    "RH",
                ),
            ),
            {"Content-Type": XLSX_MIME, "X-GreenLight-Upload": "1"},
        )
        self.assertEqual(second_status, 200)
        second_id = second_body["weather"]["weatherId"]
        self.assertNotEqual(second_id, weather["weatherId"])
        old_status, _ = self.request(
            "/api/reset",
            json.dumps(
                {
                    "scenario": "uploaded",
                    "weatherId": weather["weatherId"],
                    "runWindow": DEFAULT_WINDOW,
                    "expectedRevision": 1,
                }
            ).encode(),
            {"Content-Type": "application/json"},
        )
        self.assertEqual(old_status, 200)
        new_status, _ = self.request(
            "/api/reset",
            json.dumps(
                {
                    "scenario": "uploaded",
                    "weatherId": second_id,
                    "runWindow": DEFAULT_WINDOW,
                    "expectedRevision": 2,
                }
            ).encode(),
            {"Content-Type": "application/json"},
        )
        self.assertEqual(new_status, 200)
