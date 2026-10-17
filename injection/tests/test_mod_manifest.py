import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from injection.mods import storage
from injection.mods.storage import ModStorageService


class UnreadableManifestTests(unittest.TestCase):
    """An unreadable category manifest looked empty: its mods vanished with
    no trace, and importing a mod rewrote it with that mod alone"""

    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name)
        self.service = ModStorageService(self.root / "mods")
        self.manifest = self.root / "mods" / ModStorageService.CATEGORY_MAPS / ModStorageService.CATEGORY_METADATA
        self.manifest.parent.mkdir(parents=True, exist_ok=True)
        self.archive = self.root / "Summoner Rift.fantome"
        with zipfile.ZipFile(self.archive, "w") as zf:
            zf.writestr("WAD/Map11.wad.client", b"data")
        storage._reported_manifests.clear()

    def test_importing_does_not_overwrite_an_unreadable_manifest(self):
        corrupt = '{"version": 1, "mods": {"Old Map": {"name": "Old Map"'
        self.manifest.write_text(corrupt, encoding="utf-8")

        with self.assertLogs(level="WARNING"), self.assertRaises(ValueError):
            self.service.import_category_mod_file(ModStorageService.CATEGORY_MAPS, self.archive)

        self.assertEqual(self.manifest.read_text(encoding="utf-8"), corrupt)

    def test_importing_with_no_manifest_still_creates_it(self):
        self.service.import_category_mod_file(ModStorageService.CATEGORY_MAPS, self.archive)

        mods = json.loads(self.manifest.read_text(encoding="utf-8"))["mods"]
        self.assertEqual(list(mods), ["Summoner Rift"])

    def test_an_unreadable_manifest_is_reported_once(self):
        self.manifest.write_text("not json", encoding="utf-8")
        with self.assertLogs(level="WARNING") as logs:
            for _ in range(3):
                self.assertIsNone(ModStorageService._load_manifest(self.manifest))
        self.assertEqual(len(logs.output), 1)


class ChampionImportRollbackTests(unittest.TestCase):
    def test_failed_registration_removes_only_new_extracted_mod(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = ModStorageService(root / "mods")
            champion = service.get_champion_dir(11)
            champion.mkdir(parents=True, exist_ok=True)
            existing = champion / "Existing"
            existing.mkdir()
            (existing / "keep").write_bytes(b"old")
            archive = root / "New.fantome"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("WAD/MasterYi.wad.client", b"new")
            with patch.object(service, "set_champion_target_ids", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    service.import_mod_file(11, archive, [11001])
            self.assertEqual({p.name for p in champion.iterdir()}, {"Existing"})
            self.assertEqual((existing / "keep").read_bytes(), b"old")
            self.assertTrue(archive.exists())


if __name__ == "__main__":
    unittest.main()
