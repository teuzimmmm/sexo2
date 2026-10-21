"""The one clean start of 1.7.0 (sexo2/fresh_start.py), on temporary folders."""

import tempfile
import unittest
from pathlib import Path

from sexo2 import fresh_start


class FreshStartTests(unittest.TestCase):
    def setUp(self):
        self.local = Path(self.enterContext(tempfile.TemporaryDirectory()))
        for name in ("Rose", "SEXO2"):
            (self.local / name / "Pengu Loader" / "plugins").mkdir(parents=True)
            (self.local / name / "config.ini").write_text("[General]\n", encoding="utf-8")
        self.exe = self.local / "Downloads" / "SEXO2" / "SEXO2.exe"
        self.hooks = []

    def clean(self, busy=False):
        return fresh_start.clean(self.local, self.exe, busy, self.hooks.append)

    def test_both_folders_go_once_and_sexo2_starts_empty(self):
        self.assertEqual(len(self.clean()), 2)
        self.assertFalse((self.local / "Rose").exists())
        self.assertEqual([p.name for p in (self.local / "SEXO2").iterdir()], [fresh_start.MARKER])
        self.assertEqual(len(self.hooks), 1)
        # The next start keeps what the new version wrote
        (self.local / "SEXO2" / "config.ini").write_text("[General]\n", encoding="utf-8")
        self.assertEqual(self.clean(), [])
        self.assertTrue((self.local / "SEXO2" / "config.ini").exists())

    def test_nothing_is_deleted_while_league_or_another_sexo2_runs(self):
        self.assertEqual(self.clean(busy=True), [])
        self.assertTrue((self.local / "Rose" / "config.ini").exists())
        self.assertTrue((self.local / "SEXO2" / "config.ini").exists())
        self.assertFalse((self.local / "SEXO2" / fresh_start.MARKER).exists())

    def test_the_folder_sexo2_runs_from_is_kept(self):
        self.exe = self.local / "SEXO2" / "SEXO2.exe"
        self.assertEqual([p.name for p in self.clean()], ["Rose"])
        self.assertTrue((self.local / "SEXO2" / "config.ini").exists())

    def test_a_folder_that_could_not_be_deleted_is_tried_again(self):
        original = fresh_start.shutil.rmtree
        fresh_start.shutil.rmtree = lambda path, ignore_errors=False: None  # every file in use
        try:
            self.assertEqual(self.clean(), [])
        finally:
            fresh_start.shutil.rmtree = original
        self.assertFalse((self.local / "SEXO2" / fresh_start.MARKER).exists())
        self.assertEqual(len(self.clean()), 2)

    def test_first_start_without_old_folders_only_writes_the_marker(self):
        for name in ("Rose", "SEXO2"):
            fresh_start.shutil.rmtree(self.local / name)
        self.assertEqual(self.clean(), [])
        self.assertTrue((self.local / "SEXO2" / fresh_start.MARKER).exists())


if __name__ == "__main__":
    unittest.main()
