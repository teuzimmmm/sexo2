import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sexo2.services.game_config import _atomic_write, import_default


class GameConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "Config"
        self.config.mkdir()
        self.profile = Path(__file__).resolve().parents[1] / "assets/game-config-default.json"
        (self.config / "game.cfg").write_text("[General]\nDestinationOnly=keep\n", encoding="utf-8")
        (self.config / "input.ini").write_text("[GameEvents]\nevtSelfCastSpell1=[Alt][q]\n", encoding="utf-8")
        (self.config / "PersistedSettings.json").write_text(
            json.dumps({"accountMetadata": "keep", "files": []}), encoding="utf-8"
        )
        self.original = {p.name: p.read_bytes() for p in self.config.iterdir()}

    def apply(self, **kwargs):
        return import_default(
            directory=self.config, profile_path=self.profile, backup_root=self.root / "backups", **kwargs
        )

    def test_confirmation_and_closed_game_required_without_writing(self):
        for confirmed, running in ((False, False), ("true", False), (True, True)):
            with self.assertRaises(ValueError):
                self.apply(confirmed=confirmed, running=lambda: running)
            self.assertEqual(self.original, {p.name: p.read_bytes() for p in self.config.iterdir()})
        self.assertFalse((self.root / "backups").exists())

    def test_import_keeps_metadata_and_unknown_options_with_exact_backup(self):
        result = self.apply(confirmed=True, running=lambda: False)
        self.assertTrue(result["success"])
        for name, content in self.original.items():
            self.assertEqual((Path(result["backup"]) / name).read_bytes(), content)
        cfg = (self.config / "game.cfg").read_text()
        self.assertIn("DestinationOnly=keep", cfg)
        ini = (self.config / "input.ini").read_text()
        self.assertIn("evtSelfCastSpell1=[Shift][q]", ini)
        self.assertIn("evtPlayerAttackMoveClick=[Shift][Button 2]", ini)
        data = json.loads((self.config / "PersistedSettings.json").read_text())
        self.assertEqual(data["accountMetadata"], "keep")
        inputs = next(f for f in data["files"] if f["name"] == "input.ini")
        events = next(s for s in inputs["sections"] if s["name"] == "GameEvents")
        values = {s["name"]: s["value"] for s in events["settings"]}
        self.assertEqual(values["evtSelfCastSpell1"], "[Shift][q]")
        self.assertEqual(values["evtNormalCastSpell1"], "[<Unbound>]")

    def test_write_failure_rolls_back_already_written_files(self):
        calls = 0

        def fail_second(path, content):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("disk failure")
            _atomic_write(path, content)

        with patch("sexo2.services.game_config._atomic_write", side_effect=fail_second):
            with self.assertRaisesRegex(ValueError, "preservada"):
                self.apply(confirmed=True, running=lambda: False)
        self.assertEqual(self.original, {p.name: p.read_bytes() for p in self.config.iterdir()})

    def test_game_starting_during_preparation_blocks_writes(self):
        with self.assertRaises(ValueError):
            self.apply(confirmed=True, running=iter([False, True]).__next__)
        self.assertEqual(self.original, {p.name: p.read_bytes() for p in self.config.iterdir()})

    def test_invalid_profile_does_not_touch_game(self):
        self.profile = self.root / "invalid.json"
        self.profile.write_text('{"version":1,"files":{"../other":{}}}', encoding="utf-8")
        with self.assertRaises(ValueError):
            self.apply(confirmed=True, running=lambda: False)
        self.assertEqual(self.original, {p.name: p.read_bytes() for p in self.config.iterdir()})


if __name__ == "__main__":
    unittest.main()
