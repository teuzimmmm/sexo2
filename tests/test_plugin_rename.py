"""Plugin folders ROSE-* became SEXO2-*: the user's enabled and disabled choices must survive."""

import tempfile
import unittest
from pathlib import Path

from utils.integration import pengu_loader as pl

ROOT = Path(__file__).resolve().parent.parent
BUNDLED = ROOT / "Pengu Loader" / "plugins"


def make_plugin(plugins, name, enabled):
    folder = plugins / name
    folder.mkdir(parents=True)
    (folder / ("index.js" if enabled else "index.js_")).write_text(name, encoding="utf-8")
    return folder


class RenamedPluginTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.runtime = Path(self._temp.name)
        self.plugins = self.runtime / "plugins"
        self.plugins.mkdir()

    def names(self):
        return sorted(p.name for p in self.plugins.iterdir())

    def test_enabled_plugin_keeps_its_content_and_state(self):
        make_plugin(self.plugins, "ROSE-Hub", enabled=True)
        pl._migrate_renamed_plugins(self.runtime)
        self.assertEqual(self.names(), ["SEXO2-Hub"])
        self.assertTrue((self.plugins / "SEXO2-Hub" / "index.js").is_file())
        self.assertFalse((self.plugins / "SEXO2-Hub" / "index.js_").exists())

    def test_disabled_plugin_stays_disabled(self):
        make_plugin(self.plugins, "ROSE-RandomSkin", enabled=False)
        pl._migrate_renamed_plugins(self.runtime)
        self.assertTrue((self.plugins / "SEXO2-RandomSkin" / "index.js_").is_file())
        self.assertFalse((self.plugins / "SEXO2-RandomSkin" / "index.js").exists())

    def test_user_files_inside_the_folder_travel_with_it(self):
        folder = make_plugin(self.plugins, "ROSE-Jade", enabled=True)
        (folder / "config").mkdir()
        (folder / "config" / "mine.json").write_text("{}", encoding="utf-8")
        pl._migrate_renamed_plugins(self.runtime)
        self.assertTrue((self.plugins / "SEXO2-Jade" / "config" / "mine.json").is_file())

    def test_second_run_changes_nothing(self):
        make_plugin(self.plugins, "ROSE-UI", enabled=False)
        pl._migrate_renamed_plugins(self.runtime)
        before = self.names()
        pl._migrate_renamed_plugins(self.runtime)
        self.assertEqual(self.names(), before)
        self.assertTrue((self.plugins / "SEXO2-UI" / "index.js_").is_file())

    def test_leftover_old_folder_is_dropped_and_its_disabled_choice_carried(self):
        make_plugin(self.plugins, "ROSE-Amigos", enabled=False)
        make_plugin(self.plugins, "SEXO2-Amigos", enabled=True)
        pl._migrate_renamed_plugins(self.runtime)
        self.assertEqual(self.names(), ["SEXO2-Amigos"])
        self.assertTrue((self.plugins / "SEXO2-Amigos" / "index.js_").is_file())
        self.assertFalse((self.plugins / "SEXO2-Amigos" / "index.js").exists())

    def test_plugins_of_the_user_are_not_touched(self):
        make_plugin(self.plugins, "ROSE-Custom-Thing", enabled=True)
        make_plugin(self.plugins, "Meu-Plugin", enabled=True)
        pl._migrate_renamed_plugins(self.runtime)
        self.assertEqual(self.names(), ["Meu-Plugin", "ROSE-Custom-Thing"])

    def test_missing_plugins_folder_is_fine(self):
        pl._migrate_renamed_plugins(self.runtime / "nowhere")

    def test_state_snapshot_after_migration_sees_the_new_names(self):
        make_plugin(self.plugins, "ROSE-SkinMonitor", enabled=True)
        make_plugin(self.plugins, "ROSE-Jade", enabled=False)
        pl._migrate_renamed_plugins(self.runtime)
        enabled, disabled = pl._snapshot_plugin_enable_state(self.runtime)
        self.assertEqual((enabled, disabled), ({"SEXO2-SkinMonitor"}, {"SEXO2-Jade"}))


class BundleSyncTests(unittest.TestCase):
    def test_legacy_plugin_folders_in_the_bundle_are_not_copied(self):
        names = ["ROSE-Hub", "rose-ui", "SEXO2-Hub", "Meu-Plugin", "ROSE-Meu-Plugin"]
        ignored = pl._runtime_sync_ignore(str(Path("x") / "plugins"), names)
        self.assertEqual(ignored, {"ROSE-Hub", "rose-ui"})

    def test_datastore_is_still_ignored_and_other_folders_keep_legacy_names(self):
        self.assertEqual(pl._runtime_sync_ignore("x", ["datastore", "ROSE-Hub"]), {"datastore"})


class ShippedPluginsTests(unittest.TestCase):
    def test_every_renamed_plugin_ships_under_its_new_name_only(self):
        shipped = {p.name for p in BUNDLED.iterdir() if p.is_dir()}
        for name in pl.RENAMED_PLUGINS:
            self.assertIn(pl.PLUGIN_PREFIX + name, shipped)
        self.assertEqual({n for n in shipped if n.casefold() in pl.LEGACY_PLUGIN_NAMES}, set())

    def test_installer_removes_old_bundled_plugin_folders(self):
        text = (ROOT / "installer-sexo2.iss").read_bytes().decode("utf-8-sig")
        self.assertIn("plugins\\ROSE-*", text)


if __name__ == "__main__":
    unittest.main()
