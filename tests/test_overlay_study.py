"""The overlay study (sexo2/overlay/study.py), without the game or PresentMon."""

import json
import tempfile
import time
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

    def test_the_whole_match_is_read_and_each_offer_kept_once(self):
        answers = iter(
            [
                {"activePlayer": {"level": 1}},
                {"activePlayer": {"level": 2, "augments": ["A", "B", "C"]}},
                {"activePlayer": {"level": 2, "augments": ["A", "B", "C"]}},  # same offer
                RuntimeError("game loading"),
                {"activePlayer": {"level": 5, "augments": ["D", "E", "F"]}},
            ]
        )

        def fetch():
            answer = next(answers)
            if isinstance(answer, Exception):
                raise answer
            return answer

        probe = study._LiveProbe(fetch)
        for _ in range(5):
            probe.read_once()
        result = probe.result()
        self.assertEqual([s["value"] for s in result["augmentSamples"]], [["A", "B", "C"], ["D", "E", "F"]])
        self.assertEqual(result["errors"], 1)
        self.assertIn("activePlayer.level", result["fields"])

    def test_the_probe_runs_as_a_real_thread(self):
        probe = study._LiveProbe(lambda: {"activePlayer": {"level": 3}}, every=0.01)
        probe.start()
        deadline = time.monotonic() + 1.0
        while not probe.fields and time.monotonic() < deadline:
            time.sleep(0.01)
        probe.stop()
        probe.join(timeout=2)
        self.assertFalse(probe.is_alive())
        self.assertIn("activePlayer.level", probe.result()["fields"])

    def test_three_matches_then_never_again(self):
        self.assertEqual(study.done_matches(self.dir / "missing"), 0)
        for i in range(3):
            (self.dir / f"{study.PREFIX}{i}.json").write_text("{}", encoding="utf-8")
        (self.dir / f"{study.PREFIX}0-nada.csv").write_text("", encoding="utf-8")
        self.assertEqual(study.done_matches(self.dir), study.MATCHES)

    def test_a_try_without_frames_does_not_count_until_three_have_failed(self):
        def write(name, frames):
            windows = {"nada": {"frames": frames}, "janela": {"frames": frames}}
            (self.dir / f"{study.PREFIX}{name}.json").write_text(json.dumps({"windows": windows}), encoding="utf-8")

        write("a", 0)
        write("b", 0)
        self.assertEqual(study.done_matches(self.dir), 0)  # PresentMon measured nothing: still to do
        write("c", 1800)
        self.assertEqual(study.done_matches(self.dir), 1)
        write("d", 0)
        self.assertEqual(study.done_matches(self.dir), study.MATCHES)  # three tries measured nothing: stop

    def test_a_silent_presentmon_leaves_what_it_said(self):
        from types import SimpleNamespace
        from unittest.mock import patch

        csv_path = self.dir / "x.csv"
        csv_path.write_text("Application,MsBetweenPresents\n", encoding="utf-8")
        thread = study.OverlayStudyThread(SimpleNamespace(phase="InProgress"))
        done = SimpleNamespace(returncode=5, stderr="error: no session", stdout="")
        with (
            patch.object(study.subprocess, "run", return_value=done),
            patch.object(study, "presentmon_path", return_value=csv_path),
        ):
            result = thread._measure(csv_path)
        self.assertEqual(result["frames"], 0)
        self.assertEqual(result["exit"], 5)
        self.assertIn("no session", result["output"])
        self.assertIn("MsBetweenPresents", result["csvHead"])

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
