import tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import Mock, patch
from types import SimpleNamespace
from friends.service import FriendsService
from state import SharedState
from main.runtime.loop import _process_ui_updates, _compute_main_loop_sleep


class PerformanceTests(unittest.TestCase):
    def test_browsing_never_decompresses_whole_archive_but_validation_does(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "test.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("WAD/test", "valid content")
            resolver = Mock()
            resolver.resolve_zip.return_value = archive
            manager = SimpleNamespace(injector=SimpleNamespace(zip_resolver=resolver))
            service = FriendsService(SharedState(), Mock(), manager, root)
            with patch.object(zipfile.ZipFile, "testzip", return_value=None) as check:
                self.assertTrue(service.available(11, 11001))
                check.assert_not_called()
                self.assertTrue(service.archive(11, 11001))
                check.assert_called_once()

    def test_match_skips_catalogue_and_position_work_but_processes_pending_cleanup(self):
        ui = Mock()
        ui.has_pending_operations.return_value = True
        state = SimpleNamespace(phase="InProgress")
        scraper = Mock()
        with patch("ui.core.user_interface._user_interface", ui):
            self.assertFalse(_process_ui_updates(state, scraper))
        ui.process_pending_operations.assert_called_once()
        ui.check_resolution_and_update.assert_not_called()
        scraper.scrape_champion_skins.assert_not_called()

    def test_match_does_not_create_client_ui(self):
        with (
            patch("ui.core.user_interface._user_interface", None),
            patch("ui.core.user_interface.get_user_interface") as create,
        ):
            self.assertFalse(_process_ui_updates(SimpleNamespace(phase="GameStart"), Mock()))
        create.assert_not_called()

    def test_stale_client_flags_do_not_force_fast_loop_in_match(self):
        from config import MAIN_LOOP_IDLE_SLEEP

        state = SimpleNamespace(
            phase="InProgress", champion_exchange_triggered=True, chroma_panel_open=True, pending_chroma_selection=True
        )
        self.assertEqual(_compute_main_loop_sleep(state, True), max(MAIN_LOOP_IDLE_SLEEP, 0.25))
