"""The test overlay takes only the program file and the plugins that differ from the release."""

import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts import build_test_overlay as overlay


class OverlayTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.new = self.dir / "new"
        self.base = self.dir / "base.zip"
        self.out = self.dir / "out.zip"

    def write_new(self, files):
        for name, data in files.items():
            path = self.new / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def write_base(self, files):
        with zipfile.ZipFile(self.base, "w") as z:
            for name, data in files.items():
                z.writestr(name, data)

    def test_only_the_program_and_the_plugins_that_differ(self):
        same = {"_internal/python314.dll": b"py", "_internal/Pengu Loader/plugins/A/index.js": b"a"}
        self.write_base({**same, "SEXO2.exe": b"old", "_internal/Pengu Loader/plugins/B/index.js": b"old-b"})
        self.write_new(
            {
                **same,
                "SEXO2.exe": b"new",
                "_internal/Pengu Loader/plugins/B/index.js": b"new-b",
                "_internal/Pengu Loader/plugins/C/index.js": b"brand new",
                # an old tool restored by the build: never part of the overlay, even if it differs
                "_internal/injection/tools/ltk_patcher_host.exe": b"OLD TOOL",
                "_internal/hosting-tools/cloudflared.exe": b"x",
                "SEXO2 Update.exe": b"u",
            }
        )
        changed = overlay.build(self.base, self.new, self.out, "v1.9.0")
        self.assertEqual(
            changed,
            [
                "SEXO2.exe",
                "_internal/Pengu Loader/plugins/B/index.js",
                "_internal/Pengu Loader/plugins/C/index.js",
            ],
        )
        with zipfile.ZipFile(self.out) as z:
            self.assertEqual(sorted(z.namelist()), sorted([*changed, "LEIA-ME.txt"]))
            self.assertEqual(z.read("SEXO2.exe"), b"new")
            text = z.read("LEIA-ME.txt").decode("utf-8")
        self.assertIn("v1.9.0", text)
        self.assertIn("Feche o SEXO2", text)

    def test_a_different_python_runtime_makes_no_overlay(self):
        self.write_base({"_internal/python313.dll": b"py", "SEXO2.exe": b"old"})
        self.write_new({"_internal/python314.dll": b"py", "SEXO2.exe": b"new"})
        with self.assertRaisesRegex(ValueError, "runtime"):
            overlay.build(self.base, self.new, self.out)
        self.assertFalse(self.out.exists())
        self.assertEqual(overlay.main(["--base", str(self.base), "--new", str(self.new), "--output", str(self.out)]), 2)

    def test_without_the_program_there_is_nothing_to_overlay(self):
        self.write_base({"_internal/python314.dll": b"py"})
        self.write_new({"_internal/python314.dll": b"py"})
        with self.assertRaises(ValueError):
            overlay.build(self.base, self.new, self.out)

    def test_an_identical_plugin_is_left_out(self):
        files = {"_internal/python314.dll": b"py", "_internal/Pengu Loader/plugins/A/index.js": b"a"}
        self.write_base({**files, "SEXO2.exe": b"old"})
        self.write_new({**files, "SEXO2.exe": b"new"})
        self.assertEqual(overlay.build(self.base, self.new, self.out), ["SEXO2.exe"])


if __name__ == "__main__":
    unittest.main()
