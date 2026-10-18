import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from utils.integration import pengu_loader as loader


class PenguLifecycleTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        for name, value in (
            ("_SESSION_FILE", root / "session.json"),
            ("_ACTIVE_FLAG", root / "active.flag"),
            ("_restart_pending", frozenset()),
        ):
            self.enterContext(patch.object(loader, name, value))
        self.running = self.enterContext(patch.object(loader, "_is_league_running", return_value=True))
        self.enterContext(patch.object(loader, "_is_available", return_value=True))
        self.other = self.enterContext(patch.object(loader, "_hook_of_another_loader", return_value=None))
        self.status = self.enterContext(patch.object(loader, "get_status", return_value=loader.PenguStatus.ACTIVE))
        self.deactivate = self.enterContext(patch.object(loader, "deactivate", return_value=True))
        self.restart = self.enterContext(patch.object(loader, "restart_client", return_value=False))
        # No test may reach a real loader executable or change the user's registry.
        self.enterContext(patch.object(loader, "_run_cli_result", side_effect=AssertionError("unexpected real CLI")))
        self.assertTrue(loader._write_session(was_active=False, rose_activated=True))

    def test_quit_keeps_loaded_plugins_and_recovery_record_while_league_is_open(self):
        self.assertTrue(loader.deactivate_on_exit())
        self.deactivate.assert_not_called()
        self.restart.assert_not_called()
        self.assertTrue(loader._SESSION_FILE.is_file())
        self.assertTrue(loader._session_requires_deactivation(loader._read_session()))

    def test_reopening_adopts_the_activation_instead_of_toggling_it_off_and_on(self):
        with (
            patch.object(loader, "_external_pengu_with_rose_plugins", return_value=None),
            patch.object(loader, "_ensure_loader_config"),
            patch.object(loader, "_process_running", return_value=True),
            patch.object(loader, "_process_ids", return_value=frozenset({123})),
            patch.object(loader, "activate") as activate,
        ):
            self.assertTrue(loader.deactivate_on_exit())
            self.assertTrue(loader.cleanup_if_dirty())
            self.assertTrue(loader.activate_on_start())
        self.deactivate.assert_not_called()
        activate.assert_not_called()
        self.assertTrue(loader._session_requires_deactivation(loader._read_session()))

    def test_quit_without_league_restores_and_clears_the_owned_activation(self):
        self.running.return_value = False
        self.assertTrue(loader.deactivate_on_exit())
        self.deactivate.assert_called_once()
        self.restart.assert_not_called()
        self.assertFalse(loader._SESSION_FILE.exists())

    def test_next_start_without_league_cleans_a_retained_session(self):
        self.assertTrue(loader.deactivate_on_exit())
        self.running.return_value = False
        self.assertTrue(loader.cleanup_if_dirty())
        self.deactivate.assert_called_once()
        self.assertFalse(loader._SESSION_FILE.exists())

    def test_windows_session_cleanup_still_deactivates_with_league_open(self):
        self.assertTrue(loader.restore_after_rose())
        self.deactivate.assert_called_once()
        self.assertFalse(loader._SESSION_FILE.exists())

    def test_another_loaders_hook_is_never_deactivated(self):
        self.other.return_value = Path("external/core.dll")
        self.assertTrue(loader.deactivate_on_exit())
        self.deactivate.assert_not_called()
        self.restart.assert_not_called()
        self.assertFalse(loader._SESSION_FILE.exists())

    def test_a_preexisting_external_session_is_not_owned_by_sexo2(self):
        self.assertTrue(loader._write_session(was_active=True, rose_activated=False))
        self.assertTrue(loader.deactivate_on_exit())
        self.deactivate.assert_not_called()
        self.assertFalse(loader._SESSION_FILE.exists())

    def test_unknown_status_retains_recovery_state_without_changing_the_hook(self):
        self.status.return_value = loader.PenguStatus.UNKNOWN
        self.assertFalse(loader.deactivate_on_exit())
        self.deactivate.assert_not_called()
        self.assertTrue(loader._SESSION_FILE.exists())

    def test_legacy_ownership_flag_survives_quit_while_league_is_open(self):
        loader._SESSION_FILE.unlink()
        loader._ACTIVE_FLAG.write_text("active", encoding="utf-8")
        self.assertTrue(loader.deactivate_on_exit())
        self.deactivate.assert_not_called()
        self.assertTrue(loader._ACTIVE_FLAG.exists())

    def test_exit_cancels_a_queued_client_restart(self):
        loader._restart_pending = frozenset({123})
        self.assertTrue(loader.deactivate_on_exit())
        with patch.object(loader.threading, "Thread") as thread:
            loader.retry_deferred_restart()
        thread.assert_not_called()
        self.restart.assert_not_called()


class PenguRestartSafetyTests(unittest.TestCase):
    def test_matchmaking_and_champion_select_never_restart_the_client(self):
        for phase in ("Matchmaking", "ReadyCheck", "ChampSelect", "InProgress", "Reconnect"):
            with self.subTest(phase=phase):
                connection = Mock(ok=True, base="https://127.0.0.1:12345")
                connection.session.get.return_value.status_code = 200
                connection.session.get.return_value.json.return_value = phase
                with (
                    patch.object(loader, "_process_running", return_value=False),
                    patch("lcu.core.lcu_connection.LCUConnection", return_value=connection),
                ):
                    self.assertFalse(loader.restart_client())
                connection.session.post.assert_not_called()
                connection.session.close.assert_called_once()

    def test_a_running_game_prevents_even_attempting_a_client_restart(self):
        with (
            patch.object(loader, "_process_running", return_value=True),
            patch("lcu.core.lcu_connection.LCUConnection") as connection,
        ):
            self.assertFalse(loader.restart_client())
        connection.assert_not_called()

    def test_safe_phases_still_allow_loading_the_plugins(self):
        for phase in ("None", "Lobby", "EndOfGame"):
            with self.subTest(phase=phase):
                connection = Mock(ok=True, base="https://127.0.0.1:12345")
                connection.session.get.return_value.status_code = 200
                connection.session.get.return_value.json.return_value = phase
                connection.session.post.return_value.status_code = 204
                with (
                    patch.object(loader, "_process_running", return_value=False),
                    patch("lcu.core.lcu_connection.LCUConnection", return_value=connection),
                ):
                    self.assertTrue(loader.restart_client())
                connection.session.post.assert_called_once_with(
                    connection.base + "/riotclient/kill-and-restart-ux", timeout=5
                )
                connection.session.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
