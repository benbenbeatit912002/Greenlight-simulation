from __future__ import annotations

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


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
        asset_paths = [urlsplit(asset).path for asset in assets]
        self.assertEqual(
            asset_paths,
            ["simulator-engine.js", "app.js", "styles.css"],
        )
        for asset in asset_paths:
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
        self.assertIn("languageToggle", self.parser.ids)
        self.assertIn("controlPanel", self.parser.ids)
        self.assertIn("toggleLanguage", self.app_js)
        self.assertIn('byId("controlPanel").lang', self.app_js)
        self.assertIn("engineDisplayState", self.app_js)
        self.assertIn("translateViolation", self.app_js)

    def test_public_showcase_and_language_contract(self) -> None:
        for metadata in (
            'name="theme-color"',
            'name="application-name"',
            'property="og:title"',
            'property="og:description"',
        ):
            self.assertIn(metadata, self.html)

        for element_id in (
            "showcaseTitle",
            "showcaseStartButton",
            "tourButton",
            "projectDialog",
            "tourCloseButton",
            "tourModelCard",
            "tourExploreButton",
        ):
            self.assertIn(element_id, self.parser.ids)

        self.assertIn('aria-haspopup="dialog"', self.html)
        self.assertIn('aria-describedby="tourIntro"', self.html)
        self.assertIn('id="tourModelCard" data-engine="browser" aria-labelledby="tourModelTitle" aria-live="polite"', self.html)
        self.assertIn("openProjectDialog", self.app_js)
        self.assertIn("showModal", self.app_js)
        self.assertIn("focusSimulatorControls", self.app_js)
        self.assertIn("document.documentElement.lang = documentLanguage", self.app_js)
        self.assertNotIn('${reason ? ` ${reason}` : ""}', self.app_js)

        translation_keys = set(re.findall(r'data-i18n="([A-Za-z0-9_]+)"', self.html))
        translation_keys.update(re.findall(r'data-i18n-aria-label="([A-Za-z0-9_]+)"', self.html))
        zh_block = self.app_js.split("zh: {", 1)[1].split("},\n    en: {", 1)[0]
        en_block = self.app_js.split("en: {", 1)[1].split("},\n  };", 1)[0]
        for key in sorted(translation_keys):
            self.assertRegex(zh_block, rf"\b{re.escape(key)}:\s*\"")
            self.assertRegex(en_block, rf"\b{re.escape(key)}:\s*\"")

    def test_decision_comparison_contract(self) -> None:
        for element_id in (
            "comparisonTitle",
            "saveBaselineButton",
            "clearBaselineButton",
            "comparisonEmpty",
            "comparisonContent",
            "baselineScenario",
            "baselineStrategy",
            "candidateScenario",
            "candidateStrategy",
            "comparisonStatus",
            "comparisonContext",
            "comparisonHeatDelta",
            "comparisonLampDelta",
            "comparisonCo2Delta",
            "comparisonCostDelta",
            "comparisonFruitDelta",
            "comparisonAlertDelta",
        ):
            self.assertIn(element_id, self.parser.ids)

        self.assertIn("greenlight-decision-baseline-v1", self.app_js)
        self.assertIn("function createRunSummary", self.app_js)
        self.assertIn("function renderComparison", self.app_js)
        self.assertIn("function comparisonStrategy", self.app_js)
        self.assertIn("baselineRun.engine === candidate.engine", self.app_js)
        self.assertIn("baselineRun.runId === candidate.runId", self.app_js)
        self.assertIn("baselineRun.modelStep === candidate.modelStep", self.app_js)
        self.assertIn("if (!comparable)", self.app_js)
        self.assertIn("window.localStorage.setItem(BASELINE_STORAGE_KEY", self.app_js)
        self.assertIn("window.localStorage.removeItem(BASELINE_STORAGE_KEY", self.app_js)

        zh_block = self.app_js.split("zh: {", 1)[1].split("},\n    en: {", 1)[0]
        en_block = self.app_js.split("en: {", 1)[1].split("},\n  };", 1)[0]
        for key in (
            "replaceBaseline",
            "comparisonReadyToSave",
            "baselineNeedsRun",
            "comparisonNeedsCandidate",
            "comparisonReady",
            "comparisonStepMismatch",
            "comparisonEngineMismatch",
            "comparisonWeatherMatch",
            "comparisonWeatherDifference",
            "comparisonMeta",
            "comparisonAutoStrategy",
            "comparisonManualStrategy",
        ):
            self.assertRegex(zh_block, rf"\b{re.escape(key)}:\s*\"")
            self.assertRegex(en_block, rf"\b{re.escape(key)}:\s*\"")

        strategy = (ROOT / "PRODUCT_STRATEGY.md").read_text(encoding="utf-8")
        self.assertIn("explainable, pre-deployment greenhouse decision-support workbench", strategy)
        self.assertIn("USDA Agricultural Research Service", strategy)
        self.assertIn("Wageningen University & Research", strategy)

    def test_worklog_index_links_exist(self) -> None:
        worklog_dir = ROOT / "worklogs"
        index = (worklog_dir / "index.html").read_text(encoding="utf-8")
        links = re.findall(r'<a href="([^"/]+\.html)"', index)
        self.assertGreater(len(links), 0)
        for link in links:
            self.assertTrue((worklog_dir / link).is_file(), link)


if __name__ == "__main__":
    unittest.main()
