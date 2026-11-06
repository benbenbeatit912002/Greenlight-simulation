from __future__ import annotations

import json
import re
import tomllib
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LICENSE_ID = "AGPL-3.0-or-later"


class FooterLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_footer = False
        self.links = {}

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "footer" and values.get("class") == "legal-footer":
            self.in_footer = True
        if self.in_footer and tag == "a":
            self.links[values["data-i18n"]] = values

    def handle_endtag(self, tag):
        if tag == "footer":
            self.in_footer = False


class LicenseMetadataTests(unittest.TestCase):
    def test_project_metadata_agrees_on_license(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
        for metadata in (project, package, lock["packages"][""]):
            self.assertEqual(metadata["license"], LICENSE_ID)
        for name in project["license-files"]:
            self.assertTrue((ROOT / name).is_file())
        self.assertIn("LICENSE", project["license-files"])
        self.assertTrue(package["private"])
        self.assertEqual(project["optional-dependencies"]["greenlight"], ["gl-gym==0.3.2"])

    def test_complete_agpl_text_and_explicit_scope_are_present(self):
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("GNU AFFERO GENERAL PUBLIC LICENSE", license_text)
        self.assertIn("Version 3, 19 November 2007", license_text)
        for section in range(18):
            self.assertRegex(license_text, rf"(?m)^  {section}\. ")
        self.assertIn("END OF TERMS AND CONDITIONS", license_text)
        self.assertIn("How to Apply These Terms to Your New Programs", license_text)
        notice = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        for text in (
            LICENSE_ID,
            "Hao Yu Liu",
            "Bart van Laatum",
            "David Katzin",
            "without warranty",
        ):
            self.assertIn(text, notice)
        self.assertIn("does not replace third-party", notice)
        self.assertIn("does not assign a new license to NASA data", notice)

    def test_model_source_offer_matches_locked_source(self):
        lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
        model = next(item for item in lock["package"] if item["name"] == "gl-gym")
        self.assertEqual(model["version"], "0.3.2")
        notice = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        self.assertIn(model["sdist"]["url"], notice)
        self.assertIn(model["sdist"]["hash"].removeprefix("sha256:"), notice)

    def test_footer_offers_source_license_and_upstream_credit(self):
        footer = FooterLinks()
        footer.feed((ROOT / "index.html").read_text(encoding="utf-8"))
        expected = {
            "sourceCode": "https://github.com/benbenbeatit912002/Greenlight-simulation",
            "softwareLicense": "LICENSE",
            "modelCredits": "CITATION.md",
            "thirdPartyNotices": "THIRD_PARTY_NOTICES.md",
        }
        for key, href in expected.items():
            self.assertEqual(footer.links[key]["href"], href)
            self.assertEqual(footer.links[key]["target"], "_blank")
            self.assertIn("noopener", footer.links[key]["rel"])

    def test_public_guides_no_longer_claim_license_is_undecided(self):
        for name in ("README.md", "CONTRIBUTING.md", "docs/installation.md", "docs/roadmap.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIsNone(
                re.search(
                    r"does not yet have a software license|license remains undecided|"
                    r"license still needs to be selected",
                    text,
                ),
                name,
            )


if __name__ == "__main__":
    unittest.main()
