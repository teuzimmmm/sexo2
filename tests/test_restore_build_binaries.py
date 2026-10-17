"""Build-only binaries come back from a previous SEXO2 folder; source plugins are untouched."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from restore_build_binaries import restore  # noqa: E402


class RestoreBuildBinariesTests(unittest.TestCase):
    def test_copies_executables_from_a_nested_baseline_and_leaves_plugins_alone(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            internal = root / "baseline" / "SEXO2" / "_internal"
            for rel in (
                "Pengu Loader/Pengu Loader.exe",
                "Pengu Loader/core.dll",
                "injection/tools/mod-tools.exe",
                "hosting-tools/cloudflared.exe",
                "Pengu Loader/plugins/ROSE-UI/index.js",
            ):
                (internal / rel).parent.mkdir(parents=True, exist_ok=True)
                (internal / rel).write_text(rel)
            target = root / "repo"
            (target / "Pengu Loader/plugins/ROSE-UI").mkdir(parents=True)
            (target / "Pengu Loader/plugins/ROSE-UI/index.js").write_text("source")
            copied = restore(root / "baseline", target)
            self.assertEqual(len(copied), 4)
            self.assertTrue((target / "injection/tools/mod-tools.exe").is_file())
            self.assertEqual((target / "Pengu Loader/plugins/ROSE-UI/index.js").read_text(), "source")

    def test_missing_baseline_fails(self):
        with tempfile.TemporaryDirectory() as temp, self.assertRaises(SystemExit):
            restore(Path(temp), Path(temp) / "repo")


if __name__ == "__main__":
    unittest.main()
