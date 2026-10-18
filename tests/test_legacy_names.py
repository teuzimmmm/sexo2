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


if __name__ == "__main__":
    unittest.main()
