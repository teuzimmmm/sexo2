"""The inherited Rose telemetry stays removed (master plan, milestone M1)."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {"vendor", ".git", "tests", "docs", "build", "dist"}


class NoTelemetryTests(unittest.TestCase):
    def test_no_source_reaches_the_rose_analytics_server(self):
        offenders = []
        for path in ROOT.rglob("*"):
            if path.suffix not in {".py", ".js", ".spec", ".ps1"} or SKIP & set(path.relative_to(ROOT).parts):
                continue
            if "rosekeys" in path.read_text(encoding="utf-8", errors="ignore"):
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])

    def test_analytics_package_is_gone(self):
        self.assertEqual(list((ROOT / "analytics").rglob("*.py")), [])


if __name__ == "__main__":
    unittest.main()
