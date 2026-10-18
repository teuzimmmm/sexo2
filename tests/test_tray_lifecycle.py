import unittest
from unittest.mock import Mock, patch
from PIL import Image
from utils.integration.tray_manager import TrayManager
from state.core.app_status import AppStatus


class TrayLifecycleTests(unittest.TestCase):
    def test_early_status_does_not_wait_and_is_applied_when_backend_ready(self):
        tray = TrayManager()
        with patch("threading.Event.wait", side_effect=AssertionError("blocked startup")):
            tray.set_status("unlocked")
        self.assertEqual(tray._current_status, "unlocked")
        locked = Image.new("RGBA", (16, 16), "black")
        ready = Image.new("RGBA", (16, 16), "white")
        tray._locked_icon_image = locked
        tray._unlocked_icon_image = ready
        with (
            patch.object(tray, "_get_icon_image", return_value=locked),
            patch("utils.integration.tray_manager.pystray.Icon") as factory,
        ):
            tray._run_tray()
            self.assertIs(factory.return_value.icon, ready)
            factory.return_value.run_detached.assert_called_once()
        self.assertTrue(tray.is_running())

    def test_detached_backend_prevents_duplicate_start(self):
        tray = TrayManager()
        tray.icon = Mock()
        tray._ready_event.set()
        tray.tray_thread = Mock()
        tray.tray_thread.is_alive.return_value = False
        with patch("utils.integration.tray_manager.threading.Thread") as thread:
            tray.start()
            thread.assert_not_called()
        self.assertTrue(tray.is_running())
        tray.stop()
        self.assertFalse(tray.is_running())

    def test_repeated_status_does_not_redraw_unchanged_icon(self):
        tray = TrayManager()
        tray.icon = Mock()
        tray._base_icon_image = Image.new("RGBA", (16, 16))
        tray.set_status("unlocked")
        tray.icon.reset_mock()
        tray.set_status("unlocked")
        tray.icon.update_menu.assert_not_called()

    def test_preview_check_stops_at_first_result(self):
        def images():
            yield "first.png"
            raise AssertionError("walked the entire library")

        folder = Mock()
        folder.exists.return_value = True
        folder.rglob.return_value = images()
        with patch("state.core.app_status.get_skins_dir", return_value=folder):
            self.assertTrue(AppStatus().check_previews_downloaded())

    def test_empty_previews_still_report_not_ready(self):
        folder = Mock()
        folder.exists.return_value = True
        folder.rglob.return_value = iter(())
        with patch("state.core.app_status.get_skins_dir", return_value=folder):
            self.assertFalse(AppStatus().check_previews_downloaded())
