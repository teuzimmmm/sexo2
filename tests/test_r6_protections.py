import io, json, queue, tempfile, unittest, zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from tests import test_friends_features as fixtures
from friends.selection_guard import mark_manual, is_manual
from friends.preferences import Preferences
from friends.room import RoomService
from utils.download.verified_file import write_download
from friends.auto_accept import AutoAccept


class AutoAcceptTests(unittest.TestCase):
    def setUp(self):
        self.lcu = Mock(ok=True)
        self.phase = "ReadyCheck"
        self.response = {"state": "InProgress", "playerResponse": "None"}
        self.lcu.get.side_effect = lambda path: self.phase if "gameflow-phase" in path else self.response
        self.lcu.accept_ready_check.return_value = True
        self.accept = AutoAccept(self.lcu)

    def test_disabled_by_default(self):
        self.accept.tick("ReadyCheck")
        self.lcu.accept_ready_check.assert_not_called()

    def test_accept_once_and_new_ready_check(self):
        self.accept.enabled = True
        self.accept.tick("ReadyCheck")
        self.accept.tick("ReadyCheck")
        self.lcu.accept_ready_check.assert_called_once()
        self.accept.tick("Matchmaking")
        self.accept.tick("ReadyCheck")
        self.assertEqual(self.lcu.accept_ready_check.call_count, 2)

    def test_declined_never_reaccepted(self):
        self.accept.enabled = True
        self.response["playerResponse"] = "Declined"
        self.accept.tick("ReadyCheck")
        self.lcu.accept_ready_check.assert_not_called()

    def test_phase_changed_before_post(self):
        self.accept.enabled = True
        self.phase = "ChampSelect"
        self.accept.tick("ReadyCheck")
        self.lcu.accept_ready_check.assert_not_called()

    def test_failures_are_bounded(self):
        self.accept.enabled = True
        self.lcu.accept_ready_check.return_value = False
        for _ in range(10):
            self.accept.next_attempt = 0
            self.accept.tick("ReadyCheck")
        self.assertEqual(self.lcu.accept_ready_check.call_count, 3)


class SelectionTests(unittest.TestCase):
    setUp = fixtures.ServiceTests.setUp
    get = fixtures.ServiceTests.get

    def test_favorites_editor_works_without_a_selected_champion(self):
        self.phase = "None"
        self.ids = []
        self.lcu.get.side_effect = lambda path: (
            [{"id": 11, "name": "Master Yi"}, {"id": 22, "name": "Ashe"}, {"id": 60022, "name": "Ashe"}]
            if path.endswith("champion-summary.json")
            else self.get(path)
        )
        listed = self.service.handle({"action": "library-list"})
        self.assertEqual([c["championId"] for c in listed["libraryChampions"]], [22, 11])
        opened = self.service.handle({"action": "library-open", "championId": 22})
        self.assertEqual(opened["browseChampion"]["championId"], 22)
        result = self.service.handle({"action": "favorite", "championId": 22, "skinId": 22001, "enabled": True})
        self.assertTrue(next(s for s in result["browseChampion"]["skins"] if s["skinId"] == 22001)["favorite"])
        self.assertEqual(Preferences(self.service.preferences.path).data["favorites"]["22"], [22001])
        self.lcu.set_my_selection_skin.assert_not_called()

    def test_no_favorites_falls_back_to_available_random(self):
        self.service.handle({"action": "automatic", "mode": "favorites"})
        self.assertIn(self.state.historic_skin_id, [11001, 11002])
        count = self.lcu.set_my_selection_skin.call_count
        self.service.snapshot()
        self.assertEqual(self.lcu.set_my_selection_skin.call_count, count)

    def test_favorites_only(self):
        self.service.preferences.favorite(11, 11002, True)
        self.service.handle({"action": "automatic", "mode": "favorites"})
        self.assertEqual(self.state.historic_skin_id, 11002)

    def test_missing_favorite_falls_back(self):
        self.service.preferences.favorite(11, 11003, True)
        self.service.handle({"action": "automatic", "mode": "favorites"})
        self.assertIn(self.state.historic_skin_id, [11001, 11002])

    def test_manual_survives_automatic_and_profile_sync(self):
        mark_manual(self.state)
        self.service.preferences.save_profile("Test", {"11": {"skinId": 11002}})
        self.service.preferences.activate("Test")
        self.service.snapshot()
        self.lcu.set_my_selection_skin.assert_not_called()
        self.service.preferences.automatic("random")
        self.service.snapshot()
        self.lcu.set_my_selection_skin.assert_not_called()

    def test_new_champion_releases_manual_context(self):
        mark_manual(self.state)
        self.assertTrue(is_manual(self.state))
        self.state.locked_champ_id = 22
        self.ids = [22]
        self.assertFalse(is_manual(self.state))
        self.service.handle({"action": "automatic", "mode": "random"})
        self.assertIn(self.state.historic_skin_id, [22001, 22002])

    def test_in_progress_never_applies(self):
        self.phase = "InProgress"
        self.service.handle({"action": "automatic", "mode": "random"})
        self.lcu.set_my_selection_skin.assert_not_called()

    def test_injection_in_progress_never_applies(self):
        self.service.manager._injection_in_progress = True
        self.service.handle({"action": "automatic", "mode": "random"})
        self.lcu.set_my_selection_skin.assert_not_called()

    def test_no_eligible_preserves_selection(self):
        self.service.preferences.exclusions([11001, 11002])
        self.service.handle({"action": "automatic", "mode": "random"})
        self.lcu.set_my_selection_skin.assert_not_called()
        self.assertTrue(self.service.last_message)

    def test_corrupt_zip_detected_and_fixed_file_rechecked(self):
        path = self.root / "skins/11/11001/11001.zip"
        data = path.read_bytes()
        path.write_bytes(data.replace(b"test", b"xxxx", 1))
        self.service._file_cache.clear()
        self.assertFalse(self.service.archive(11, 11001))
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("WAD/test.wad.client", "repaired")
        self.service._file_cache.clear()
        self.assertTrue(self.service.archive(11, 11001))

    def test_room_link_excluded_from_diagnostic(self):
        self.service.room.link = "https://example.com/#rose=" + "SECRET" * 8
        with patch("friends.service.export_report") as exporter:
            exporter.return_value = self.root / "diagnostic.zip"
            self.service.handle({"action": "export-diagnostic"})
            self.assertNotIn("room", exporter.call_args.args[1])


class PersistenceTests(unittest.TestCase):
    def test_autoaccept_disk_failure_is_reported(self):
        from config import set_config_option

        with (
            tempfile.TemporaryDirectory() as directory,
            patch("config.get_config_file_path", return_value=Path(directory) / "config.ini"),
            patch("config.write_config_file", side_effect=OSError("disk full")),
        ):
            with self.assertRaises(ValueError):
                set_config_option("General", "autoaccept", "true", strict=True)

    def test_backup_restore_preserves_corrupt_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prefs.json"
            p = Preferences(path)
            p.favorite(11, 11001, True)
            p.favorite(11, 11002, True)
            path.write_text("broken")
            p = Preferences(path)
            self.assertTrue(p.error)
            p.restore_backup()
            self.assertIsNone(p.error)
            self.assertEqual(p.data["favorites"]["11"], [11001])
            self.assertEqual(next(path.parent.glob("*.preservado-*")).read_text(), "broken")

    def test_disk_error_keeps_preferences_and_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prefs.json"
            p = Preferences(path)
            p.favorite(11, 11001, True)
            before = path.read_bytes()
            with patch("friends.preferences.atomic_write", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    p.favorite(11, 11002, True)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(p.data["favorites"]["11"], [11001])


class DownloadTests(unittest.TestCase):
    def response(self, data, length=None, error=False):
        response = Mock()
        response.headers = {"Content-Length": str(len(data) if length is None else length)}

        def chunks(chunk_size):
            yield data[:5]
            if error:
                raise OSError("connection lost")
            yield data[5:]

        response.iter_content = chunks
        return response

    def test_interrupted_download_preserves_old_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "skin.zip"
            path.write_bytes(b"old")
            with self.assertRaises(OSError):
                write_download(self.response(b"new content", error=True), path)
            self.assertEqual(path.read_bytes(), b"old")
            self.assertEqual(len(list(path.parent.iterdir())), 1)

    def test_wrong_length_preserves_old_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "skin.zip"
            path.write_bytes(b"old")
            with self.assertRaises(ValueError):
                write_download(self.response(b"bad", 100), path)
            self.assertEqual(path.read_bytes(), b"old")

    def test_corrupt_zip_preserves_old_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "skin.zip"
            path.write_bytes(b"old")
            with self.assertRaises(zipfile.BadZipFile):
                write_download(self.response(b"not a zip"), path)
            self.assertEqual(path.read_bytes(), b"old")

    def test_valid_zip_commits(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("WAD/data", "skin")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "skin.zip"
            write_download(self.response(buf.getvalue()), path)
            self.assertEqual(path.read_bytes(), buf.getvalue())


class RoomTests(unittest.TestCase):
    def room(self):
        host = Mock()
        host.events = queue.Queue()
        host.thread = None
        return RoomService(SimpleNamespace(), host), host

    def test_ready_saves_and_reconnects(self):
        service, host = self.room()
        host.events.put(("ready", "https://test/#rose=secret"))
        with patch("friends.room.save_server_link") as save, patch.object(service, "reconnect") as connect:
            state = service.poll()
            self.assertTrue(state["hosting"])
            save.assert_called_once()
            connect.assert_called_once()

    def test_storage_failure_stops_host(self):
        service, host = self.room()
        host.events.put(("ready", "https://test/#rose=secret"))
        with patch("friends.room.save_server_link", side_effect=OSError("disk")):
            result = service.poll()
            self.assertEqual(result["status"], "error")
            self.assertIsNone(result["link"])
            host.stop.assert_called_once()

    def test_join_allowed_during_champ_select(self):
        service, host = self.room()
        service.state.phase = "ChampSelect"
        with patch("friends.room.save_server_link") as save, patch.object(service, "reconnect") as connect:
            service.handle("room-join", {"link": "https://test/#rose=secret"})
            save.assert_called_once()
            connect.assert_called_once()


if __name__ == "__main__":
    unittest.main()
