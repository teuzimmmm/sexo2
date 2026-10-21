"""The on-screen warning for an LTK patcher the installed game has outgrown (D-150)."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from injection.overlay import overlay_manager
from injection.tools import patcher_notice
from injection.tools.patcher_notice import LTK_PATCHER_FILES_URL, notice_text, notify_patcher_outdated

YES, NO, CANCEL = 6, 7, 2


class PatcherNoticeTests(unittest.TestCase):
    def setUp(self):
        patcher_notice.forget_shown()
        self.addCleanup(patcher_notice.forget_shown)
        self.tools = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.urls, self.folders, self.shown = [], [], []

    def notify(self, answer, eol="2026-10-04 04:00"):
        def show(title, body):
            self.shown.append((title, body))
            return answer

        return notify_patcher_outdated(
            self.tools,
            eol,
            show=show,
            open_url=self.urls.append,
            open_folder=self.folders.append,
            background=False,
        )

    def test_the_text_says_what_happened_and_where_the_two_files_are(self):
        title, body = notice_text("2026-10-04 04:00")
        self.assertIn("Patcher desatualizado", title)
        self.assertIn(LTK_PATCHER_FILES_URL, body)
        self.assertIn("ltk_patcher_host.exe", body)
        self.assertIn("ltk_patcher_dll.dll", body)
        self.assertIn("2026-10-04 04:00", body)

    def test_the_link_is_the_folder_of_the_two_files(self):
        self.assertEqual(
            LTK_PATCHER_FILES_URL, "https://github.com/LeagueToolkit/ltk-manager/tree/main/src-tauri/resources"
        )

    def test_yes_opens_the_page_no_opens_the_folder_cancel_opens_nothing(self):
        self.assertTrue(self.notify(YES, "a"))
        self.assertEqual((self.urls, self.folders), ([LTK_PATCHER_FILES_URL], []))
        self.assertTrue(self.notify(NO, "b"))
        self.assertEqual(self.folders, [self.tools])
        self.assertTrue(self.notify(CANCEL, "c"))
        self.assertEqual((len(self.urls), len(self.folders)), (1, 1))

    def test_it_warns_once_per_end_of_life_date(self):
        self.assertTrue(self.notify(CANCEL, "2026-10-04 04:00"))
        self.assertFalse(self.notify(CANCEL, "2026-10-04 04:00"))  # the next failed injection stays quiet
        self.assertEqual(len(self.shown), 1)
        self.assertTrue(self.notify(CANCEL, "2026-11-01 04:00"))  # another patcher, another warning

    def test_a_failure_to_show_never_raises(self):
        def broken(title, body):
            raise OSError("no desktop")

        self.assertTrue(
            notify_patcher_outdated(self.tools, "x", show=broken, open_url=self.urls.append, background=False)
        )

    def test_it_runs_in_its_own_thread_so_the_injection_is_not_held(self):
        done = mock.Mock(return_value=CANCEL)
        started = notify_patcher_outdated(self.tools, "t", show=done, open_url=self.urls.append)
        self.assertTrue(started)


class ExpiredPatcherInTheInjectionTests(unittest.TestCase):
    def test_an_expired_patcher_is_listed_and_warned_about(self):
        manager = overlay_manager.OverlayManager.__new__(overlay_manager.OverlayManager)
        with (
            mock.patch.object(overlay_manager, "report_issue") as report,
            mock.patch.object(overlay_manager, "notify_patcher_outdated") as notify,
        ):
            manager._handle_expired_patcher(Path("tools"), "2026-10-04 04:00")
        self.assertEqual(report.call_args.args[0], "LTK_PATCHER_EOL")
        notify.assert_called_once_with(Path("tools"), "2026-10-04 04:00")


if __name__ == "__main__":
    unittest.main()
