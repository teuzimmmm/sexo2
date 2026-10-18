"""Bridge messages carry mod paths; deletion must stay inside the champion folder."""

import tempfile
import unittest
from pathlib import Path

from injection.mods.storage import ModStorageService


class ModDeleteTraversalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "mods"
        self.storage = ModStorageService(self.root)
        self.outside = Path(self.tmp.name) / "keep.txt"
        self.outside.write_text("user file")
        self.champion_dir = self.storage.get_champion_dir(103)
        self.champion_dir.mkdir(parents=True, exist_ok=True)
        self.sibling = self.storage.get_champion_dir(222)
        self.sibling.mkdir(parents=True, exist_ok=True)
        (self.sibling / "other.fantome").write_text("x")

    def test_traversal_paths_delete_nothing(self):
        rel = self.champion_dir.relative_to(self.root).as_posix()
        absolute = str(self.outside)
        for relative_path in (
            "../keep.txt",
            f"{rel}/../../keep.txt",
            "../../keep.txt",
            "..",
            "..\\keep.txt",
            f"{rel}\\..\\..\\keep.txt",
            absolute,
            "/" + absolute.lstrip("/"),
        ):
            self.assertFalse(self.storage.delete_champion_mod(103, relative_path=relative_path), relative_path)
        for mod_name in ("../keep.txt", "..", "../../keep.txt"):
            self.assertFalse(self.storage.delete_champion_mod(103, mod_name=mod_name), mod_name)
        self.assertTrue(self.outside.exists())

    def test_another_champions_mod_is_not_reachable(self):
        sibling_rel = (self.sibling / "other.fantome").relative_to(self.root).as_posix()
        self.assertFalse(self.storage.delete_champion_mod(103, relative_path=sibling_rel))
        self.assertTrue((self.sibling / "other.fantome").exists())

    def test_own_mod_is_deleted(self):
        mod = self.champion_dir / "mine.fantome"
        mod.write_text("x")
        self.assertTrue(self.storage.delete_champion_mod(103, relative_path=mod.relative_to(self.root).as_posix()))
        self.assertFalse(mod.exists())


if __name__ == "__main__":
    unittest.main()
