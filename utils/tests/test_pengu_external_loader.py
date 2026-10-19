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


if __name__ == "__main__":
    unittest.main()
