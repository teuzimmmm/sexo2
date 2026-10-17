"""Every place that shows or stamps the release version agrees with sexo2/version.py (M2)."""
import re
import unittest
from pathlib import Path

import config
from sexo2.services.settings import SettingsService
from sexo2.version import RELEASE_VERSION

ROOT = Path(__file__).resolve().parent.parent


class VersionConsistencyTests(unittest.TestCase):
    def test_release_version_is_semantic(self):
        self.assertRegex(RELEASE_VERSION, r"^\d+\.\d+\.\d+$")

    def test_executable_metadata_matches(self):
        text = (ROOT / "assets" / "sexo2-version.txt").read_text(encoding="utf-8")
        numeric = RELEASE_VERSION.replace(".", ",") + ",0"
        self.assertIn(f"filevers=({numeric})", text)
        self.assertIn(f"prodvers=({numeric})", text)
        self.assertIn(f"StringStruct('FileVersion','{RELEASE_VERSION}.0')", text)
        self.assertIn(f"StringStruct('ProductVersion','{RELEASE_VERSION}.0')", text)

    def test_installer_matches(self):
        text = (ROOT / "installer-sexo2.iss").read_bytes().decode("utf-8-sig")
        self.assertEqual(re.findall(r'#define MyAppVersion "([^"]*)"', text), [RELEASE_VERSION + ".0"])

    def test_settings_panel_shows_the_release(self):
        service = SettingsService(validate_path=lambda p: False, autostart_status=lambda: False,
                                  set_autostart=lambda v: None, infer_client_path=lambda p: p)
        self.assertEqual(service.snapshot()["version"], RELEASE_VERSION)

    def test_http_requests_identify_the_release(self):
        self.assertEqual(config.APP_USER_AGENT, f"SEXO2/{RELEASE_VERSION}")

    def test_inherited_protocol_version_is_unchanged(self):
        # The party relay and the legacy launcher compare this value; it is not the release.
        self.assertEqual(config.APP_VERSION, "1.4.7")


if __name__ == "__main__":
    unittest.main()
