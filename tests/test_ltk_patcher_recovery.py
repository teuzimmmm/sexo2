"""The user's LTK patcher files follow SEXO2 between versions without being shipped."""

import tempfile
import unittest
from pathlib import Path

from injection.tools.patcher import LTK_PATCHER_DLL, LTK_PATCHER_HOST, recover_ltk_patcher


def put(folder: Path, content: bytes = b"v1") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / LTK_PATCHER_HOST).write_bytes(b"host" + content)
    (folder / LTK_PATCHER_DLL).write_bytes(b"dll" + content)
    return folder


class PatcherRecoveryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.tools = root / "new" / "_internal" / "injection" / "tools"
        self.tools.mkdir(parents=True)
        self.data = root / "data"
        self.old_install = root / "old"
        self.previous = [self.old_install / "_internal" / "injection" / "tools"]

    def recover(self):
        recover_ltk_patcher(self.tools, self.data / "tools", self.previous)

    def test_files_come_from_the_previous_installation_and_are_kept(self):
        put(self.old_install / "_internal" / "injection" / "tools")
        self.recover()
        self.assertEqual((self.tools / LTK_PATCHER_DLL).read_bytes(), b"dllv1")
        self.assertEqual((self.data / "tools" / LTK_PATCHER_HOST).read_bytes(), b"hostv1")

    def test_kept_copy_serves_the_next_version(self):
        put(self.data / "tools")
        self.recover()
        self.assertEqual((self.tools / LTK_PATCHER_HOST).read_bytes(), b"hostv1")

    def test_newer_files_placed_by_the_user_replace_the_kept_copy(self):
        put(self.data / "tools", b"v1")
        put(self.tools, b"v2")
        self.recover()
        self.assertEqual((self.data / "tools" / LTK_PATCHER_DLL).read_bytes(), b"dllv2")
        self.assertEqual((self.tools / LTK_PATCHER_DLL).read_bytes(), b"dllv2")

    def test_nothing_found_leaves_the_folder_for_the_dialog(self):
        self.recover()
        self.assertFalse((self.tools / LTK_PATCHER_HOST).exists())


if __name__ == "__main__":
    unittest.main()
