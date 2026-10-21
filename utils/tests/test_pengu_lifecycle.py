"""Closing and reopening SEXO2 while League runs (no real loader or registry is touched)."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        self.clients = frozenset({4242})
        self.enterContext(patch.object(loader, "_process_ids", side_effect=lambda names: self.clients))
        self.enterContext(patch.object(loader, "_process_running", side_effect=lambda names: bool(self.clients)))
        self.enterContext(patch.object(loader, "_is_league_running", side_effect=lambda: bool(self.clients)))
        self.enterContext(patch.object(loader, "_is_available", return_value=True))
        # The real process list (a League client open on the developer machine) must not leak in.
        self.enterContext(patch.object(loader, "_client_start_times", return_value=[]))
        self.other = self.enterContext(patch.object(loader, "_hook_of_another_loader", return_value=None))
        self.status = self.enterContext(patch.object(loader, "get_status", return_value=loader.PenguStatus.ACTIVE))
        self.deactivate = self.enterContext(patch.object(loader, "deactivate", return_value=True))
        self.activate = self.enterContext(patch.object(loader, "activate", return_value=True))
        self.restart = self.enterContext(patch.object(loader, "restart_client", return_value=True))
        self.enterContext(patch.object(loader, "_external_pengu_with_app_plugins", return_value=None))
        self.enterContext(patch.object(loader, "_ensure_loader_config"))
        # No test may reach a real loader executable or change the user's registry.
        self.enterContext(patch.object(loader, "_run_cli_result", side_effect=AssertionError("unexpected real CLI")))
        self.assertTrue(loader._write_session(was_active=False, app_activated=True))

    def test_quitting_with_league_open_keeps_the_plugins_and_restarts_nothing(self):
        self.assertTrue(loader.deactivate_on_exit())
        self.deactivate.assert_not_called()
        self.restart.assert_not_called()
        session = loader._read_session()
        self.assertEqual(session["clients_with_plugins"], [4242])
        self.assertTrue(loader._session_requires_deactivation(session))

    def test_reopening_with_the_same_client_does_not_restart_it(self):
        loader.deactivate_on_exit()
        self.assertTrue(loader.activate_on_start())
        self.activate.assert_not_called()
        self.deactivate.assert_not_called()
        self.restart.assert_not_called()
        self.assertEqual(loader._read_session()["clients_with_plugins"], [])

    def test_reopening_with_a_new_client_restarts_it_to_load_the_plugins(self):
        loader.deactivate_on_exit()
        self.clients = frozenset({5151})  # League was restarted meanwhile without SEXO2
        self.assertTrue(loader.activate_on_start())
        self.restart.assert_called_once()

    def test_quitting_before_the_client_was_restarted_switches_off(self):
        loader._restart_pending = frozenset({4242})  # the client never got the plugins
        self.assertTrue(loader.deactivate_on_exit())
        self.deactivate.assert_called_once()
        self.assertFalse(loader._SESSION_FILE.exists())

    def test_quitting_without_league_switches_off_and_clears(self):
        self.clients = frozenset()
        self.assertTrue(loader.deactivate_on_exit())
        self.deactivate.assert_called_once()
        self.restart.assert_not_called()
        self.assertFalse(loader._SESSION_FILE.exists())

    def test_windows_shutting_down_switches_off_even_with_league_open(self):
        self.assertTrue(loader.end_of_windows_session())
        self.deactivate.assert_called_once()
        self.assertFalse(loader._SESSION_FILE.exists())

    def test_another_loader_or_the_users_own_activation_is_never_kept_or_switched_off(self):
        self.other.return_value = Path("external/core.dll")
        self.assertTrue(loader.deactivate_on_exit())
        self.deactivate.assert_not_called()
        self.assertTrue(loader._write_session(was_active=True, app_activated=False))
        self.other.return_value = None
        self.assertTrue(loader.deactivate_on_exit())
        self.deactivate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
