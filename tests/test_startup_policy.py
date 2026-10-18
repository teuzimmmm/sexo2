import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch, Mock
from launcher.core import startup_policy as policy


class StartupPolicyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.files = {key: self.root / key for key in ("hashes", "skins", "classic")}
        self.files["hashes"].write_bytes(b"hashes")
        self.files["skins"].write_text("a" * 40)
        self.files["classic"].write_text('{"synced":true}')
        for target, value in [("tracked_files", self.files), ("state_path", self.root / "ready.json")]:
            context = patch.object(policy, target, return_value=value)
            context.start()
            self.addCleanup(context.stop)
        context = patch("state.AppStatus")
        status = context.start().return_value
        status.check_skins_downloaded.return_value = True
        status.check_previews_downloaded.return_value = True
        self.addCleanup(context.stop)

    def test_first_launch_requires_confirmation_then_warm_launch_skips_network(self):
        self.assertFalse(policy.can_start_fast())
        policy.record_ready()
        with patch(
            "utils.download.repo_downloader.RepoDownloader.fetch_remote_sha",
            side_effect=AssertionError("network on startup"),
        ):
            self.assertTrue(policy.can_start_fast())

    def test_changed_or_missing_local_data_invalidates_checkpoint(self):
        policy.record_ready()
        self.files["hashes"].write_bytes(b"changed")
        self.assertFalse(policy.can_start_fast())
        policy.record_ready()
        self.files["skins"].unlink()
        self.assertFalse(policy.can_start_fast())

    def test_pending_updates_wait_for_next_launch_outside_match(self):
        policy.record_ready()
        data = policy.read_state()
        data["pending"] = ["skins"]
        policy.state_path().write_text(json.dumps(data))
        with patch.object(policy, "game_running", return_value=False):
            self.assertFalse(policy.can_start_fast())
        with patch.object(policy, "game_running", return_value=True):
            self.assertTrue(policy.can_start_fast())

    def test_probe_only_schedules_updates_without_touching_content(self):
        policy.record_ready()
        before = {key: path.read_bytes() for key, path in self.files.items()}
        with (
            patch("utils.download.repo_downloader.RepoDownloader") as downloader,
            patch("utils.download.hash_updater.check_for_updates", return_value=True),
        ):
            downloader.return_value.fetch_remote_sha.return_value = "b" * 40
            downloader.return_value.get_local_sha.return_value = "a" * 40
            policy.probe_updates()
            downloader.return_value.download_incremental_updates.assert_not_called()
            downloader.return_value.download_and_extract_skins.assert_not_called()
        self.assertEqual(policy.read_state()["pending"], ["hashes", "skins"])
        self.assertEqual(before, {key: path.read_bytes() for key, path in self.files.items()})

    def test_cancelled_probe_does_not_write_pending_state(self):
        policy.record_ready()
        with patch("utils.download.repo_downloader.RepoDownloader") as downloader:
            downloader.return_value.fetch_remote_sha.return_value = "b" * 40
            policy.probe_updates(cancelled=lambda: True)
        self.assertEqual(policy.read_state()["pending"], [])

    def test_invalid_classic_marker_does_not_confirm_library(self):
        self.files["classic"].write_text('{"synced":false}')
        policy.record_ready()
        self.assertFalse(policy.can_start_fast())

    def test_corrupt_classic_marker_falls_back_instead_of_breaking_startup(self):
        self.files["classic"].write_text("[]")
        policy.record_ready()
        self.assertFalse(policy.can_start_fast())
