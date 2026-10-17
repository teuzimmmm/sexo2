import json, tempfile, threading, time, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from injection.mods.storage import ModStorageService
from pengu.communication.message_handler import MessageHandler


class LibraryBridgeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        handler = MessageHandler.__new__(MessageHandler)
        self.handler = handler
        handler._background_lock = threading.Lock()
        handler.mod_storage = ModStorageService(self.root / "mods")
        handler.shared_state = SimpleNamespace(phase="Lobby", stop=False)
        handler.injection_manager = SimpleNamespace(_injection_in_progress=False)
        handler.skin_scraper = SimpleNamespace(
            lcu=SimpleNamespace(ok=True, get=lambda path: [{"id": 22, "name": "Ashe", "alias": "Ashe"}])
        )
        handler._send_response = Mock()
        self.folder = patch("pengu.communication.message_handler.get_user_data_dir", return_value=self.root)
        self.folder.start()
        self.addCleanup(self.folder.stop)
        self.addCleanup(handler.close_library)
        handler._handle_library({"action": "list"})
        for _ in range(100):
            if handler._send_response.called:
                break
            time.sleep(0.01)

    def test_status_is_not_queued_behind_a_slow_import(self):
        release = threading.Event()
        entered = threading.Event()

        def wait(*args):
            entered.set()
            release.wait(2)

        with patch.object(self.handler._library_service, "resolve", side_effect=wait):
            self.handler._handle_library({"action": "resolve", "id": "test", "championId": 22, "targets": [22000]})
            self.assertTrue(entered.wait(1))
            self.handler._send_response.reset_mock()
            self.handler._handle_library({"action": "status"})
            self.assertTrue(self.handler._send_response.called)
            release.set()

    def test_close_stops_watcher_and_blocks_further_commit(self):
        self.handler._library_service.watching = True
        self.handler.close_library()
        self.assertFalse(self.handler._library_service.watching)
        self.assertTrue(self.handler._library_closed.is_set())
        with self.assertRaises(ValueError):
            self.handler._library_service.check_idle()
