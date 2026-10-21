"""Which registered loader SEXO2 keeps instead of its own (no registry or loader is touched)."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils.integration import pengu_loader as loader


class ExternalLoaderTests(unittest.TestCase):
    def loader_with(self, *plugins):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (root / "Pengu Loader.exe").write_bytes(b"")
        (root / "core.dll").write_bytes(b"")
        for name in plugins:
            (root / "plugins" / name).mkdir(parents=True)
            (root / "plugins" / name / "index.js").write_text("", encoding="utf-8")
        self.enterContext(patch.object(loader, "_hook_of_another_loader", return_value=root / "core.dll"))
        return root

    def test_a_standalone_pengu_with_the_sexo2_plugins_is_kept(self):
        root = self.loader_with("SEXO2-SkinMonitor", "SEXO2-UI")
        self.assertEqual(loader._external_pengu_with_app_plugins(), root)

    def test_rose_or_a_sexo2_from_before_the_rename_is_replaced(self):
        # Rose's own loader, or SEXO2 1.6.4: its core.dll shows Rose's dialog and no SEXO2 menu loads
        self.loader_with("ROSE-SkinMonitor", "ROSE-UI")
        self.assertIsNone(loader._external_pengu_with_app_plugins())

    def test_a_pengu_without_the_plugins_is_replaced(self):
        self.loader_with("SomeoneElsesPlugin")
        self.assertIsNone(loader._external_pengu_with_app_plugins())


class OlderPluginsTests(unittest.TestCase):
    """An open client loaded its plugins when it started: a restart only when they changed since."""

    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (self.root / "plugins" / "SEXO2-UI").mkdir(parents=True)
        self.script = self.root / "plugins" / "SEXO2-UI" / "index.js"
        self.script.write_text("a", encoding="utf-8")
        self.enterContext(patch.object(loader, "_PLUGINS_FILE", self.root / "state" / "pengu_plugins.json"))

    def client_started(self, at):
        return patch.object(loader, "_client_start_times", return_value=[at])

    def test_without_a_client_nothing_restarts(self):
        with self.client_started(0):
            pass
        with patch.object(loader, "_client_start_times", return_value=[]):
            self.assertFalse(loader._client_has_older_plugins(self.root))

    def test_a_client_started_before_the_plugins_were_first_seen_has_older_ones(self):
        with self.client_started(1.0):
            self.assertTrue(loader._client_has_older_plugins(self.root))

    def test_a_client_started_after_the_last_change_is_current(self):
        with self.client_started(1.0):
            self.assertTrue(loader._client_has_older_plugins(self.root))  # first sight: saved as now
        changed_at = loader._plugins_changed_at(self.root)
        with self.client_started(changed_at + 5):
            self.assertFalse(loader._client_has_older_plugins(self.root))  # same plugins, later client

    def test_a_change_in_a_plugin_makes_the_open_client_old_again(self):
        loader._plugins_changed_at(self.root)
        before = loader._plugins_changed_at(self.root)
        self.script.write_text("b", encoding="utf-8")
        with patch.object(loader.time, "time", return_value=before + 100):
            self.assertEqual(loader._plugins_changed_at(self.root), before + 100)
        with self.client_started(before + 50):
            self.assertTrue(loader._client_has_older_plugins(self.root))
        with self.client_started(before + 150):
            self.assertFalse(loader._client_has_older_plugins(self.root))

    def test_unreadable_plugins_never_restart_anything(self):
        with self.client_started(1.0), patch.object(Path, "rglob", side_effect=OSError("denied")):
            self.assertFalse(loader._client_has_older_plugins(self.root))

    def test_startup_with_its_own_loader_left_on_restarts_an_older_client_once(self):
        self.enterContext(patch.object(loader, "_hook_of_another_loader", return_value=self.root / "core.dll"))
        (self.root / "Pengu Loader.exe").write_bytes(b"")
        (self.root / "plugins" / "SEXO2-SkinMonitor").mkdir()
        (self.root / "plugins" / "SEXO2-SkinMonitor" / "index.js").write_text("", encoding="utf-8")
        self.enterContext(patch.object(loader, "PENGU_DIR", self.root))
        self.enterContext(patch.object(loader, "_write_session", return_value=True))
        self.enterContext(patch.object(loader, "_process_ids", return_value=frozenset({7})))
        restart = self.enterContext(patch.object(loader, "restart_client", return_value=True))
        with self.client_started(1.0):
            self.assertTrue(loader.activate_on_start())
        restart.assert_called_once()
        changed_at = loader._plugins_changed_at(self.root)
        with self.client_started(changed_at + 5):
            self.assertTrue(loader.activate_on_start())
        restart.assert_called_once()  # the restarted client has these plugins

    def test_a_standalone_loader_of_the_user_is_never_restarted_for_it(self):
        other = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch.object(loader, "_hook_of_another_loader", return_value=other / "core.dll"))
        (other / "Pengu Loader.exe").write_bytes(b"")
        for name in ("SEXO2-SkinMonitor", "SEXO2-UI"):
            (other / "plugins" / name).mkdir(parents=True)
            (other / "plugins" / name / "index.js").write_text("", encoding="utf-8")
        self.enterContext(patch.object(loader, "_write_session", return_value=True))
        restart = self.enterContext(patch.object(loader, "restart_client", return_value=True))
        with self.client_started(1.0):
            self.assertTrue(loader.activate_on_start())
        restart.assert_not_called()


if __name__ == "__main__":
    unittest.main()
