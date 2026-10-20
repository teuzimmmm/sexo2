"""The overlay study (sexo2/overlay/study.py), without the game or PresentMon."""

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from sexo2.overlay import study


class OverlayStudyTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def test_presentmon_csv_becomes_fps_low_and_present_modes(self):
        path = self.dir / "a.csv"
        rows = ["Application,ProcessID,PresentMode,MsBetweenPresents"]
        rows += ["League of Legends.exe,1,Hardware: Independent Flip,1.0"] * 98
        rows += ["League of Legends.exe,1,Composed: Flip,10.0"] * 2
        path.write_text("\n".join(rows), encoding="utf-8")
        summary = study.summarize_csv(path)
        self.assertEqual(summary["frames"], 100)
        self.assertAlmostEqual(summary["fps"], 1000 / 1.18, places=0)
        self.assertEqual(summary["low1"], 100.0)
        self.assertEqual(summary["modes"], {"Hardware: Independent Flip": 98, "Composed: Flip": 2})
        path.write_text("Application,MsBetweenPresents\nx,1.0\n", encoding="utf-8")
        self.assertEqual(study.summarize_csv(path), {"frames": 1})

    def test_live_api_keeps_field_names_and_augment_values_only(self):
        data = {
            "activePlayer": {"riotId": "Eu#BR1", "augments": [{"id": 1205, "name": "ADAPt"}], "level": 3},
            "allPlayers": [{"riotId": "Outro#BR1", "championName": "Ahri"}],
        }
        described = study.describe_live(data)
        self.assertIn("activePlayer.riotId", described["fields"])
        self.assertIn("allPlayers[].championName", described["fields"])
        self.assertEqual(described["augments"], {"activePlayer.augments": [{"id": 1205, "name": "ADAPt"}]})
        self.assertNotIn("Eu#BR1", json.dumps(described, default=list))

    def test_three_matches_then_never_again(self):
        self.assertEqual(study.done_matches(self.dir / "missing"), 0)
        for i in range(3):
            (self.dir / f"{study.PREFIX}{i}.json").write_text("{}", encoding="utf-8")
        (self.dir / f"{study.PREFIX}0-nada.csv").write_text("", encoding="utf-8")
        self.assertEqual(study.done_matches(self.dir), study.MATCHES)

    def test_results_go_into_the_diagnostic_zip(self):
        from friends.diagnostics import export_report

        logs = self.dir / "logs"
        logs.mkdir()
        (self.dir / "diagnostics").mkdir()
        (self.dir / "diagnostics" / f"{study.PREFIX}20261020-160000.json").write_text(
            json.dumps({"windows": {"nada": {"fps": 950.0}}}), encoding="utf-8"
        )
        target = export_report(self.dir / "out", {"members": []}, logs)
        with zipfile.ZipFile(target) as archive:
            self.assertIn(f"estudos/{study.PREFIX}20261020-160000.json", archive.namelist())


if __name__ == "__main__":
    unittest.main()
