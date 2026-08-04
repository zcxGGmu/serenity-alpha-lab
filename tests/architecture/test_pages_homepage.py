from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-pages.yml"
PAGES_URL = "https://zcxggmu.github.io/serenity-alpha-lab/"


class Parser(HTMLParser):
    pass


class HomepagePagesStructureTests(unittest.TestCase):
    def test_pages_homepage_is_static_and_linked(self) -> None:
        html_path = WEB / "index.html"
        css_path = WEB / "styles.css"

        html = html_path.read_text(encoding="utf-8")
        css = css_path.read_text(encoding="utf-8")
        Parser().feed(html)

        self.assertTrue(css_path.exists())
        self.assertNotIn("<script", html.lower())
        self.assertIn("Serenity Alpha Lab", html)
        self.assertIn("SAL-P6-005", html)
        self.assertIn("110/129", html)
        self.assertIn("https://github.com/zcxGGmu/serenity-alpha-lab", html)
        self.assertIn("focus-visible", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn("touch-action: manipulation", css)
        self.assertNotIn("font-size: clamp(", css)
        self.assertNotIn("font-size: min(", css)
        self.assertNotIn("font-size: max(", css)

    def test_pages_workflow_matches_static_web_directory_contract(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        readme = (WEB / "README.md").read_text(encoding="utf-8")

        self.assertIn("actions/configure-pages@v5", workflow)
        self.assertIn("python3 -m unittest discover -s tests/architecture -p", workflow)
        self.assertIn("actions/upload-pages-artifact@v4", workflow)
        self.assertIn("actions/deploy-pages@v4", workflow)
        self.assertIn("path: web", workflow)
        self.assertIn("branches: [main]", workflow)
        self.assertIn(PAGES_URL, readme)
        self.assertTrue((WEB / ".nojekyll").exists())


if __name__ == "__main__":
    unittest.main()
