from __future__ import annotations

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class IdCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.controls: list[str] = []
        self.scripts: list[str] = []
        self.stylesheets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        element_id = values.get("id")
        if element_id:
            self.ids.add(element_id)
        control_name = values.get("data-control")
        if control_name:
            self.controls.append(control_name)
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"] or "")
        if tag == "link" and values.get("rel") == "stylesheet":
            self.stylesheets.append(values.get("href") or "")


class StaticContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.app_js = (ROOT / "app.js").read_text(encoding="utf-8")
        cls.engine_js = (ROOT / "simulator-engine.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "styles.css").read_text(encoding="utf-8")
        cls.parser = IdCollector()
        cls.parser.feed(cls.html)

    def test_local_assets_exist(self) -> None:
        assets = self.parser.scripts + self.parser.stylesheets
        self.assertEqual(
            assets,
            ["simulator-engine.js", "app.js", "styles.css"],
        )
        for asset in assets:
            self.assertTrue((ROOT / asset).is_file(), asset)

    def test_every_app_lookup_exists_in_html(self) -> None:
        looked_up_ids = set(re.findall(r'byId\("([A-Za-z0-9_-]+)"\)', self.app_js))
        missing = looked_up_ids - self.parser.ids
        self.assertEqual(missing, set(), f"Missing HTML ids: {sorted(missing)}")

    def test_greenlight_control_contract(self) -> None:
        expected = ["uBoil", "uCO2", "uThScr", "uVent", "uLamp", "uBlScr"]
        self.assertEqual(self.parser.controls, expected)
        for name in expected:
            self.assertRegex(self.engine_js, rf'"{name}"')

    def test_no_external_runtime_dependencies(self) -> None:
        combined = "\n".join((self.html, self.app_js, self.engine_js, self.styles))
        self.assertNotRegex(combined, r"https?://(?:cdn|unpkg|esm\.)")
        self.assertNotIn("WebSocket", combined)
        api_paths = set(re.findall(r'requestApi\("(/api/[a-z]+)"', self.app_js))
        self.assertEqual(api_paths, {"/api/status", "/api/reset", "/api/step"})

    def test_accessibility_basics(self) -> None:
        self.assertIn('lang="zh-Hant"', self.html)
        self.assertIn('aria-live="polite"', self.html)
        self.assertIn('role="img"', self.html)
        self.assertIn('aria-label="模擬執行控制"', self.html)


if __name__ == "__main__":
    unittest.main()
