"""The design system holds only approved values and its generated CSS is current (M4)."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

DESIGN = Path(__file__).resolve().parent.parent / "design"


class DesignTokensTests(unittest.TestCase):
    def setUp(self):
        self.tokens = json.loads((DESIGN / "tokens.json").read_text(encoding="utf-8"))

    def test_generated_css_is_current(self):
        result = subprocess.run([sys.executable, str(DESIGN / "build_tokens.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_only_the_two_approved_families(self):
        families = {font["family"] for font in self.tokens["approved"]["font"].values()}
        self.assertEqual(families, {"Oswald", "Inter"})

    def test_font_files_and_licenses_ship_together(self):
        for font in self.tokens["approved"]["font"].values():
            self.assertTrue((DESIGN / font["file"]).is_file(), font["file"])
            self.assertTrue((DESIGN / "fonts" / f"OFL-{font['family']}.txt").is_file())

    def test_no_remote_fonts(self):
        css = (DESIGN / "tokens.css").read_text(encoding="utf-8")
        self.assertNotIn("http", css)


if __name__ == "__main__":
    unittest.main()
