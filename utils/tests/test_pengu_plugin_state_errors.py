"""A failure to keep the user's plugin on/off choices must be visible in the log."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from utils.integration import pengu_loader


class PluginStateErrorTests(unittest.TestCase):
    def test_restore_failure_is_a_warning(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "plugins").mkdir()
            with (
                patch.object(pengu_loader, "_sanitize_plugin_entrypoints", side_effect=OSError("locked")),
                self.assertLogs(pengu_loader.log, level="WARNING") as logs,
            ):
                pengu_loader._restore_plugin_enable_state(Path(temp), set(), set())
        self.assertIn("Failed to restore plugin enable state", logs.output[0])


if __name__ == "__main__":
    unittest.main()
