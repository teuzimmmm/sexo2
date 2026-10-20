import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
import unittest.mock
from unittest.mock import patch

from injection.overlay import overlay_manager, process_manager
from injection.overlay.overlay_manager import OverlayManager
from injection.overlay.process_manager import ProcessManager
from injection.tools.patcher import LTK_PATCHER_HOST


class StoppedPatcherTests(unittest.TestCase):
    """SEXO2's cleanup kills the patcher with exit code 1 (Popen) or 15 (psutil)"""

    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        self.overlay_dir = root / "overlay"
        self.overlay_dir.mkdir()
        self.process_manager = ProcessManager()
        self.overlay = OverlayManager(root / "tools", root / "mods", root / "game", self.process_manager)

        reporter = patch.object(overlay_manager, "report_issue")
        self.report_issue = reporter.start()
        self.addCleanup(reporter.stop)
        # Never touch the developer's real patcher or mod-tools processes
        self.running = []
        processes = patch.object(process_manager.psutil, "process_iter", side_effect=lambda *a, **k: list(self.running))
        processes.start()
        self.addCleanup(processes.stop)

    def _start_patcher(self):
        """Stand-in patcher that runs until it's killed"""
        proc = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        self.addCleanup(proc.stdin.close)
        self.addCleanup(lambda: proc.poll() is None and proc.kill())
        self.process_manager.current_overlay_process = proc
        reader = threading.Thread(target=lambda: None)
        reader.start()
        session = {
            "proc": proc,
            "session": {"state": None, "error": None, "eol": False},
            "reader": reader,
            "log": None,
        }
        return proc, session

    def _serve_until(self, session, stop):
        result = {}
        runner = threading.Thread(
            target=lambda: result.update(code=self.overlay._run_ltk_patcher(session, self.overlay_dir))
        )
        runner.start()
        stop()
        runner.join(timeout=15)
        self.assertFalse(runner.is_alive())
        return result["code"]

    def test_end_of_game_stop_is_not_a_failure(self):
        proc, session = self._start_patcher()
        code = self._serve_until(session, self.process_manager.stop_overlay_process)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(code, 0)
        self.report_issue.assert_not_called()

    def test_lobby_cleanup_is_not_a_failure(self):
        proc, session = self._start_patcher()
        self.running = [SimpleNamespace(info={"pid": proc.pid, "name": LTK_PATCHER_HOST})]
        code = self._serve_until(session, self.process_manager.kill_all_runoverlay_processes)
        self.assertEqual(proc.returncode, 15)
        self.assertEqual(code, 0)
        self.report_issue.assert_not_called()

    def test_patcher_dying_by_itself_is_reported(self):
        proc, session = self._start_patcher()
        code = self._serve_until(session, proc.terminate)
        self.assertEqual(code, 1)
        self.report_issue.assert_called_once()
        self.assertIn("exited with code 1", self.report_issue.call_args.args[2])

    def test_patcher_errors_are_still_reported_when_rose_stops_it(self):
        proc, session = self._start_patcher()
        session["session"]["error"] = "the game started before the patcher, overlay not applied"
        code = self._serve_until(session, self.process_manager.stop_overlay_process)
        self.assertEqual(code, 1)
        self.report_issue.assert_called_once()
        self.assertIn("overlay not applied", self.report_issue.call_args.args[2])


class GameExitTests(unittest.TestCase):
    """The game closing at the normal end of a match is not "SEXO2 lost the game"."""

    def setUp(self):
        from injection.game import match_recovery
        from injection.overlay.match_context import MatchContext

        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        self.overlay_dir = root / "overlay"
        self.overlay_dir.mkdir()
        self.process_manager = ProcessManager()
        self.overlay = OverlayManager(root / "tools", root / "mods", root / "game", self.process_manager)
        self.state = SimpleNamespace(phase="InProgress")
        self.manager = SimpleNamespace(shared_state=self.state, resume_game=lambda: None)
        self.game = {4242}
        for target, name, value in (
            (match_recovery, "game_pids", lambda: set(self.game)),
            (overlay_manager, "PROCESS_MONITOR_SLEEP_S", 0.02),
            (overlay_manager, "GAME_EXIT_GRACE_S", 1.0),
            (overlay_manager, "report_issue", unittest.mock.Mock()),
        ):
            patcher = patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.issues = []
        issue = patch.object(MatchContext, "report_issue", lambda ctx, code, *a: self.issues.append(code))
        issue.start()
        self.addCleanup(issue.stop)

    def serve(self, script):
        proc, session = StoppedPatcherTests._start_patcher(self)
        runner = threading.Thread(
            target=lambda: self.overlay._run_ltk_patcher(session, self.overlay_dir, None, self.manager)
        )
        runner.start()
        script()
        self.process_manager.stop_overlay_process()
        runner.join(timeout=15)
        self.assertFalse(runner.is_alive())

    def test_normal_end_reconnect_then_results_is_not_reported(self):
        import time

        def end_of_match():
            time.sleep(0.2)
            self.game.clear()  # the game closes
            self.state.phase = "Reconnect"  # a few seconds before the results (Arena, 20/10/2026)
            time.sleep(0.6)
            self.state.phase = "PreEndOfGame"
            time.sleep(1.0)

        self.serve(end_of_match)
        self.assertNotIn("GAME_EXIT", self.issues)

    def test_a_game_gone_while_the_match_goes_on_is_reported(self):
        import time

        def crash():
            time.sleep(0.2)
            self.game.clear()
            self.state.phase = "Reconnect"
            time.sleep(1.6)

        self.serve(crash)
        self.assertEqual(self.issues.count("GAME_EXIT"), 1)


if __name__ == "__main__":
    unittest.main()
