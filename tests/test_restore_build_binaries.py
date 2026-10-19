"""Build-only binaries come back from a previous SEXO2 folder; source plugins are untouched."""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from restore_build_binaries import apply_core, restore  # noqa: E402


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
                "Pengu Loader/plugins/SEXO2-UI/index.js",
            ):
                (internal / rel).parent.mkdir(parents=True, exist_ok=True)
                (internal / rel).write_text(rel)
            target = root / "repo"
            (target / "Pengu Loader/plugins/SEXO2-UI").mkdir(parents=True)
            (target / "Pengu Loader/plugins/SEXO2-UI/index.js").write_text("source")
            copied = restore(root / "baseline", target)
            self.assertEqual(len(copied), 4)
            self.assertTrue((target / "injection/tools/mod-tools.exe").is_file())
            self.assertEqual((target / "Pengu Loader/plugins/SEXO2-UI/index.js").read_text(), "source")

    def test_core_replaces_the_baseline_dll_only_when_the_hash_matches(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            core = root / "new-core.dll"
            core.write_bytes(b"new core")
            lock = root / "core.lock.json"
            lock.write_text(json.dumps({"sha256": hashlib.sha256(b"new core").hexdigest()}))
            target = root / "repo"
            (target / "Pengu Loader").mkdir(parents=True)
            (target / "Pengu Loader/core.dll").write_bytes(b"baseline core")
            apply_core(core, target, lock)
            self.assertEqual((target / "Pengu Loader/core.dll").read_bytes(), b"new core")
            lock.write_text(json.dumps({"sha256": "0" * 64}))
            (target / "Pengu Loader/core.dll").write_bytes(b"baseline core")
            with self.assertRaises(SystemExit):
                apply_core(core, target, lock)
            self.assertEqual((target / "Pengu Loader/core.dll").read_bytes(), b"baseline core")

    def test_missing_baseline_fails(self):
        with tempfile.TemporaryDirectory() as temp, self.assertRaises(SystemExit):
            restore(Path(temp), Path(temp) / "repo")


if __name__ == "__main__":
    unittest.main()
