"""Logs and the diagnostics summary carry the SEXO2 name; files from earlier versions are kept or cleaned."""

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import config


class LogNameTests(unittest.TestCase):
    def test_new_logs_are_sexo2_and_old_rose_logs_are_still_cleaned(self):
        self.assertTrue(Path("sexo2_17-10-2026_22-25-07.log").match(config.LOG_FILE_PATTERN))
        self.assertTrue(Path("sexo2_runoverlay_17-10-2026_22-25-07.log").match(config.LOG_FILE_PATTERN))
        from utils.core import logging as sexo2_logging

        with tempfile.TemporaryDirectory() as temp:
            logs = Path(temp) / "logs"
            logs.mkdir()
            old = time.time() - 3 * 24 * 3600
            for name in ("rose_1.log", "sexo2_1.log", "rose_runoverlay_1.log", "log_updater_1.log"):
                (logs / name).write_text("x")
                os.utime(logs / name, (old, old))
            (logs / "sexo2_new.log").write_text("x")
            with patch("utils.core.paths.get_user_data_dir", return_value=Path(temp)):
                sexo2_logging.cleanup_logs()
            self.assertEqual(sorted(p.name for p in logs.iterdir()), ["sexo2_new.log"])

    def test_diagnostics_summary_moves_to_its_new_name_once(self):
        from utils.core import issue_reporter

        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "rose_diagnostics.txt").write_text("history")
            with patch.object(issue_reporter, "get_user_data_dir", return_value=Path(temp)):
                path = issue_reporter.issues_path()
            self.assertEqual(path.name, "sexo2_diagnostics.txt")
            self.assertEqual(path.read_text(), "history")
            self.assertFalse((Path(temp) / "rose_diagnostics.txt").exists())


if __name__ == "__main__":
    unittest.main()
