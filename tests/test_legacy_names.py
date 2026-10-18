"""Names the rename left behind: files in the data folder, the mutexes, the lock file."""

import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import config
from main.core.lockfile import ERROR_ALREADY_EXISTS, acquire_instance_mutexes
from utils.core.legacy_names import migrate_file
from utils.system import admin_utils


class FakeKernel32:
    """Named mutexes as the kernel keeps them: a name that exists reports ERROR_ALREADY_EXISTS."""

    def __init__(self, existing=()):
        self.names = set(existing)
        self.last_error = 0
        self.closed = []
        self.handles = {}

    def CreateMutexW(self, _attributes, _owner, name):
        self.last_error = ERROR_ALREADY_EXISTS if name in self.names else 0
        self.names.add(name)
        handle = len(self.handles) + 1
        self.handles[handle] = name
        return handle

    def GetLastError(self):
        return self.last_error

    def CloseHandle(self, handle):
        self.closed.append(handle)


class MigrateFileTests(unittest.TestCase):
    def test_old_file_is_moved_with_its_content(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "rose_diagnostics.txt").write_text("linha antiga", encoding="utf-8")
            result = migrate_file(folder, "rose_diagnostics.txt", "sexo2_diagnostics.txt")
            self.assertEqual(result, folder / "sexo2_diagnostics.txt")
            self.assertEqual(result.read_text(encoding="utf-8"), "linha antiga")
            self.assertFalse((folder / "rose_diagnostics.txt").exists())

    def test_second_call_changes_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "rose_diagnostics.txt").write_text("a", encoding="utf-8")
            first = migrate_file(folder, "rose_diagnostics.txt", "sexo2_diagnostics.txt")
            self.assertEqual(migrate_file(folder, "rose_diagnostics.txt", "sexo2_diagnostics.txt"), first)
            self.assertEqual(first.read_text(encoding="utf-8"), "a")

    def test_existing_new_file_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "rose_diagnostics.txt").write_text("antigo", encoding="utf-8")
            (folder / "sexo2_diagnostics.txt").write_text("novo", encoding="utf-8")
            result = migrate_file(folder, "rose_diagnostics.txt", "sexo2_diagnostics.txt")
            self.assertEqual(result.read_text(encoding="utf-8"), "novo")
            self.assertTrue((folder / "rose_diagnostics.txt").exists())

    def test_nothing_to_move_gives_the_new_path(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(
                migrate_file(Path(temp), "rose_diagnostics.txt", "sexo2_diagnostics.txt"),
                Path(temp) / "sexo2_diagnostics.txt",
            )


class InstanceMutexTests(unittest.TestCase):
    NAMES = (config.SINGLE_INSTANCE_MUTEX_NAME, config.LEGACY_SINGLE_INSTANCE_MUTEX_NAME)

    def test_names_are_the_new_one_and_the_one_older_versions_hold(self):
        self.assertIn("SEXO2", config.SINGLE_INSTANCE_MUTEX_NAME)
        self.assertIn("Rose", config.LEGACY_SINGLE_INSTANCE_MUTEX_NAME)

    def test_both_names_are_taken_by_the_first_instance(self):
        kernel = FakeKernel32()
        handles = acquire_instance_mutexes(kernel, self.NAMES)
        self.assertEqual(len(handles), 2)
        self.assertEqual(kernel.names, set(self.NAMES))

    def test_a_running_old_version_blocks_the_new_one(self):
        kernel = FakeKernel32(existing={config.LEGACY_SINGLE_INSTANCE_MUTEX_NAME})
        self.assertIsNone(acquire_instance_mutexes(kernel, self.NAMES))
        self.assertEqual(len(kernel.closed), 2)

    def test_a_running_new_version_blocks_the_old_one_through_the_legacy_name(self):
        first = FakeKernel32()
        acquire_instance_mutexes(first, self.NAMES)
        old_version = FakeKernel32(existing=first.names)
        self.assertIsNone(acquire_instance_mutexes(old_version, (config.LEGACY_SINGLE_INSTANCE_MUTEX_NAME,)))

    def test_refused_creation_gives_an_empty_list(self):
        class Refusing(FakeKernel32):
            def CreateMutexW(self, *_):
                return 0

        self.assertEqual(acquire_instance_mutexes(Refusing(), self.NAMES), [])

    def test_the_installer_waits_for_both_names(self):
        text = (Path(config.__file__).parent / "installer-sexo2.iss").read_bytes().decode("utf-8-sig")
        line = next(line for line in text.splitlines() if line.startswith("AppMutex="))
        for name in self.NAMES:
            if "Dev" not in name:
                self.assertIn(name, line)


class FakeScheduler:
    """schtasks with the tasks that exist; records the deletions and creations."""

    def __init__(self, tasks):
        self.tasks = set(tasks)
        self.calls = []

    def run(self, cmd, **_):
        self.calls.append(cmd)
        action, name = cmd[1], cmd[3]
        if action == "/Query":
            return SimpleNamespace(returncode=0 if name in self.tasks else 1, stderr="")
        if action == "/Delete":
            if name not in self.tasks:
                return SimpleNamespace(returncode=1, stderr="not found")
            self.tasks.discard(name)
            return SimpleNamespace(returncode=0, stderr="")
        if action == "/Create":
            self.tasks.add(name)
            return SimpleNamespace(returncode=0, stderr="")
        raise AssertionError(cmd)


class AutostartTaskTests(unittest.TestCase):
    def run_with(self, tasks, action):
        scheduler = FakeScheduler(tasks)
        no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        with (
            patch.object(admin_utils.subprocess, "run", scheduler.run),
            patch.object(admin_utils.subprocess, "CREATE_NO_WINDOW", no_window, create=True),
            patch.object(admin_utils, "is_admin", return_value=True),
        ):
            return scheduler, action()

    def test_a_task_of_an_older_version_counts_as_registered(self):
        _, registered = self.run_with({"Rose"}, admin_utils.is_registered_for_autostart)
        self.assertTrue(registered)

    def test_no_task_means_not_registered(self):
        _, registered = self.run_with(set(), admin_utils.is_registered_for_autostart)
        self.assertFalse(registered)

    def test_registering_creates_the_new_task_and_drops_the_old_one(self):
        scheduler, (ok, _) = self.run_with({"Rose"}, admin_utils.register_autostart)
        self.assertTrue(ok)
        self.assertEqual(scheduler.tasks, {"SEXO2"})

    def test_registering_twice_changes_nothing(self):
        scheduler, (ok, message) = self.run_with({"SEXO2"}, admin_utils.register_autostart)
        self.assertTrue(ok)
        self.assertIn("Already", message)
        self.assertFalse([c for c in scheduler.calls if c[1] == "/Create"])

    def test_unregistering_removes_both_names(self):
        scheduler, (ok, _) = self.run_with({"SEXO2", "Rose"}, admin_utils.unregister_autostart)
        self.assertTrue(ok)
        self.assertEqual(scheduler.tasks, set())

    def test_unregistering_only_the_old_task(self):
        scheduler, (ok, _) = self.run_with({"Rose"}, admin_utils.unregister_autostart)
        self.assertTrue(ok)
        self.assertEqual(scheduler.tasks, set())


class RelayEnvironmentTests(unittest.TestCase):
    def test_new_and_old_variable_names_are_read(self):
        from party.network.private_server_config import relay_url_from_environment

        with patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(relay_url_from_environment())
        with patch.dict("os.environ", {"ROSE_RELAY_URL": "wss://old"}, clear=True):
            self.assertEqual(relay_url_from_environment(), "wss://old")
        with patch.dict("os.environ", {"ROSE_RELAY_URL": "wss://old", "SEXO2_RELAY_URL": "wss://new"}, clear=True):
            self.assertEqual(relay_url_from_environment(), "wss://new")


class RoomCodeFormatTests(unittest.TestCase):
    """Codes and links friends on older versions produce and read."""

    def test_written_code_keeps_the_prefix_older_versions_expect(self):
        from party.protocol.token_codec import create_token

        self.assertTrue(create_token(1234).encode().startswith("ROSE:"))

    def test_code_is_read_with_either_prefix_or_none(self):
        from party.protocol.token_codec import create_token, PartyToken

        token = create_token(1234)
        body = token.encode()[len("ROSE:") :]
        for text in ("ROSE:" + body, "SEXO2:" + body, body):
            decoded = PartyToken.decode(text)
            self.assertEqual(decoded.summoner_id, 1234)
            self.assertEqual(decoded.encryption_key, token.encryption_key)

    def test_room_link_is_read_with_either_fragment(self):
        from party.network.private_server_config import parse_server_link

        key = "A" * 43
        old = parse_server_link(f"https://sala.example/#rose={key}")
        new = parse_server_link(f"https://sala.example/#sexo2={key}")
        self.assertEqual(old, new)
        self.assertEqual(old[1], key)

    def test_room_link_written_by_the_host_keeps_the_old_fragment(self):
        source = (Path(config.__file__).parent / "party" / "hosting" / "controller.py").read_text(encoding="utf-8")
        self.assertIn('"/#rose=" + token', source)

    def test_diagnostic_hides_both_fragments(self):
        from friends.diagnostics import sanitize

        for name in ("rose", "sexo2"):
            self.assertNotIn("AAAA", sanitize(f"link #{name}=AAAAAAAA"))


class PenguSessionFileTests(unittest.TestCase):
    """The session file a version before the rename left behind after a crash."""

    def test_old_keys_still_say_the_app_activated_pengu(self):
        from utils.integration.pengu_loader import _session_requires_deactivation

        self.assertTrue(_session_requires_deactivation({"rose_activated_pengu": True}))
        self.assertFalse(
            _session_requires_deactivation({"rose_activated_pengu": True, "pengu_was_active_before_rose": True})
        )
        self.assertFalse(_session_requires_deactivation({"rose_activated_pengu": False}))

    def test_new_keys_are_read_and_win_over_old_ones(self):
        from utils.integration.pengu_loader import _session_requires_deactivation

        self.assertTrue(_session_requires_deactivation({"app_activated_pengu": True}))
        self.assertFalse(
            _session_requires_deactivation({"app_activated_pengu": True, "pengu_was_active_before_app": True})
        )
        self.assertFalse(_session_requires_deactivation({"app_activated_pengu": False, "rose_activated_pengu": True}))


class ImportLeftoverTests(unittest.TestCase):
    def test_import_leftovers_of_both_names_are_not_listed_as_mods(self):
        from injection.mods.storage import ModStorageService

        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "mods"
            for name in (".rose-import-abc", ".sexo2-import-abc", "Real Mod"):
                (folder / name).mkdir(parents=True)
            service = ModStorageService(Path(temp) / "store")
            entries = service._list_mods_in_directory(folder, 1, 1000)
            self.assertEqual([e.mod_name for e in entries], ["Real Mod"])


if __name__ == "__main__":
    unittest.main()
