"""The data folder moves from %LOCALAPPDATA%\\Rose to %LOCALAPPDATA%\\SEXO2 once, keeping everything."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils.core.paths import _data_dir_in


def old_layout(parent: Path) -> Path:
    old = parent / "Rose"
    (old / "mods" / "skins").mkdir(parents=True)
    (old / "mods" / "skins" / "ahri.fantome").write_bytes(b"mod")
    (old / "config.ini").write_text("[General]\nthreshold = 0.5\n", encoding="utf-8")
    (old / "friends-preferences.json").write_text('{"version": 2}', encoding="utf-8")
    return old


class DataFolderMigrationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.parent = Path(tmp.name)

    def test_rose_folder_is_moved_with_its_files(self):
        old_layout(self.parent)
        folder = _data_dir_in(self.parent)
        self.assertEqual(folder, self.parent / "SEXO2")
        self.assertFalse((self.parent / "Rose").exists())
        self.assertEqual((folder / "mods" / "skins" / "ahri.fantome").read_bytes(), b"mod")
        self.assertEqual((folder / "friends-preferences.json").read_text(encoding="utf-8"), '{"version": 2}')
        self.assertTrue((folder / "config.ini").exists())

    def test_existing_sexo2_folder_wins_and_rose_is_left_alone(self):
        old_layout(self.parent)
        (self.parent / "SEXO2").mkdir()
        self.assertEqual(_data_dir_in(self.parent), self.parent / "SEXO2")
        self.assertTrue((self.parent / "Rose" / "config.ini").exists())

    def test_fresh_install_uses_sexo2(self):
        self.assertEqual(_data_dir_in(self.parent), self.parent / "SEXO2")

    def test_folder_in_use_keeps_rose_for_this_start(self):
        old_layout(self.parent)
        with patch.object(Path, "rename", side_effect=PermissionError("in use")):
            self.assertEqual(_data_dir_in(self.parent), self.parent / "Rose")
        self.assertEqual(_data_dir_in(self.parent), self.parent / "SEXO2")  # next start

    def test_program_installed_in_sexo2_is_never_mixed_with_data(self):
        old_layout(self.parent)
        (self.parent / "SEXO2").mkdir()
        (self.parent / "SEXO2" / "SEXO2.exe").write_bytes(b"MZ")
        self.assertEqual(_data_dir_in(self.parent), self.parent / "Rose")


if __name__ == "__main__":
    unittest.main()
