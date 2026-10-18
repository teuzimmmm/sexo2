import json, tempfile, time, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import requests
from friends.arena_bravery import ArenaBravery, bravery_selected


class BraveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = SimpleNamespace(stop=False, current_game_mode="CHERRY")
        self.lcu = Mock()
        self.lcu.phase = "InProgress"
        self.manager = Mock()
        self.manager._initialized = True
        self.manager._injection_in_progress = False
        self.manager.recovery.cancelled.is_set.return_value = False
        self.manager.injector.game_dir = self.root
        self.manager.injector.tools_dir = self.root
        patcher = patch("injection.tools.patcher.check_ltk_patcher")
        self.patcher = patcher.start()
        self.patcher.return_value.missing = []
        self.patcher.return_value.expired_for.return_value = False
        self.addCleanup(patcher.stop)
        self.controller = ArenaBravery(self.lcu, self.state, self.manager, self.root)
        self.controller.armed = True
        self.controller.started = time.monotonic()
        self.session = {
            "localPlayerCellId": 2,
            "myTeam": [{"cellId": 2, "slotId": 2, "championId": -3}],
            "actions": [[{"actorCellId": 2, "type": "pick", "completed": True, "championId": -3}]],
        }
        self.detail = {"isSelf": True, "skinSplashPath": "/video/cherry/bravery-animated-splash.webm"}
        self.service = Mock()
        self.service.preferences.error = None
        self.service.preferences.snapshot.return_value = {"excluded": [], "favorites": {}, "automatic": "off"}
        self.service.load_library.return_value = [{"championId": 11}]
        self.service.catalogs.catalog.return_value = {"skins": [{"skinId": 11001, "name": "Test"}]}
        self.service.archive.return_value = True
        self.service.recents.return_value = []
        self.state.friends_service = self.service
        self.game = {
            "gameData": {
                "gameId": 999,
                "queue": {"gameMode": "CHERRY"},
                "teamOne": [{"puuid": "me", "championId": 11}],
                "teamTwo": [],
            }
        }
        self.lcu.get.side_effect = lambda uri: self.game if "gameflow/v1/session" in uri else {"puuid": "me"}
        self.process = Mock()
        self.process.exe.return_value = str(self.root / "League of Legends.exe")
        self.process.create_time.return_value = 100

    def run_prepare(self):
        with (
            patch("injection.game.match_recovery.game_pids", return_value={321}),
            patch("psutil.Process", return_value=self.process),
        ):
            self.controller._prepare()

    def execute(self, label, callback):
        return callback(None)

    def test_explicit_marker_and_own_completed_pick_required(self):
        self.assertTrue(bravery_selected(self.session))
        for cid in (-2, -1, 0, 11):
            self.session["myTeam"][0]["championId"] = cid
            self.assertFalse(bravery_selected(self.session))
        self.session["myTeam"][0]["championId"] = -3
        self.session["actions"][0][0]["completed"] = False
        self.assertFalse(bravery_selected(self.session))

    def test_other_player_completed_is_not_enough(self):
        self.session["actions"][0][0]["actorCellId"] = 3
        self.assertFalse(bravery_selected(self.session, self.detail))

    def test_one_restart_and_overlay_before_reconnect(self):
        self.manager._run_injection.side_effect = self.execute

        def overlay(*args, **kwargs):
            self.lcu.reconnect_game.assert_not_called()
            self.assertTrue(self.manager.arena_overlay_ready())
            return True

        self.manager.injector.inject_skin.side_effect = overlay
        self.run_prepare()
        self.process.terminate.assert_called_once()
        self.manager.injector.inject_skin.assert_called_once()
        self.lcu.reconnect_game.assert_called_once()
        self.assertIsNone(self.manager.arena_overlay_ready)
        self.run_prepare()
        self.process.terminate.assert_called_once()

    def test_restart_of_app_does_not_repeat_same_match(self):
        self.controller.marker.write_text(json.dumps({"gameId": "999"}))
        self.run_prepare()
        self.manager._run_injection.assert_not_called()
        self.process.terminate.assert_not_called()

    def test_no_skin_no_close(self):
        self.service.archive.return_value = False
        self.run_prepare()
        self.process.terminate.assert_not_called()

    def test_wrong_mode_no_close(self):
        self.game["gameData"]["queue"]["gameMode"] = "CLASSIC"
        self.run_prepare()
        self.process.terminate.assert_not_called()

    def test_injection_busy_no_close(self):
        self.manager._injection_in_progress = True
        self.run_prepare()
        self.process.terminate.assert_not_called()

    def test_emergency_stop_no_close(self):
        self.manager.recovery.cancelled.is_set.return_value = True
        self.run_prepare()
        self.process.terminate.assert_not_called()

    def test_wrong_process_path_no_close(self):
        self.process.exe.return_value = str(self.root / "LeagueClient.exe")
        self.run_prepare()
        self.process.terminate.assert_not_called()

    def test_failed_overlay_returns_to_game_without_skin(self):
        self.manager._run_injection.side_effect = self.execute
        self.manager.injector.inject_skin.side_effect = RuntimeError("failed preparation")
        with self.assertRaises(RuntimeError):
            self.run_prepare()
        self.lcu.reconnect_game.assert_called_once()
        self.assertIsNone(self.manager.arena_overlay_ready)

    def test_loading_api_not_ready_keeps_waiting(self):
        self.lcu.get.side_effect = requests.ConnectionError("still loading")
        self.controller._attempt()
        self.assertTrue(self.controller.armed)
        self.assertFalse(self.controller.running)
        self.process.terminate.assert_not_called()

    def test_corrupt_restart_guard_fails_closed(self):
        self.controller.marker.write_text("broken")
        self.run_prepare()
        self.process.terminate.assert_not_called()

    def test_early_window_expired_no_restart(self):
        self.controller.started = time.monotonic() - 100
        self.run_prepare()
        self.process.terminate.assert_not_called()

    def test_marker_must_be_saved_before_close(self):
        self.manager._run_injection.side_effect = self.execute
        with patch("friends.arena_bravery.atomic_write", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.run_prepare()
        self.process.terminate.assert_not_called()

    def test_manual_champion_selection_disarms(self):
        self.lcu.get.side_effect = lambda uri: (
            self.session if uri.endswith("/session") else {"isSelf": True, "championIconStyle": "normal"}
        )
        self.session["myTeam"][0]["championId"] = 11
        self.controller.tick("ChampSelect")
        self.assertFalse(self.controller.armed)

    def test_idle_phase_disarms_but_null_does_not(self):
        self.controller.tick(None)
        self.assertTrue(self.controller.armed)
        self.controller.last_poll = 0
        self.controller.tick("Lobby")
        self.assertFalse(self.controller.armed)

    def test_missing_or_expired_patcher_does_not_close_game(self):
        self.patcher.return_value.expired_for.return_value = True
        self.run_prepare()
        self.process.terminate.assert_not_called()

    def test_favorites_preferred_and_exclusions_respected(self):
        self.service.preferences.snapshot.return_value = {
            "excluded": [11002],
            "favorites": {"11": [11003]},
            "automatic": "favorites",
        }
        self.service.catalogs.catalog.return_value = {
            "skins": [{"skinId": 11001, "name": "A"}, {"skinId": 11002, "name": "B"}, {"skinId": 11003, "name": "C"}]
        }
        self.manager._run_injection.side_effect = self.execute
        self.manager.injector.inject_skin.side_effect = lambda *a, **k: self.manager.arena_overlay_ready()
        self.run_prepare()
        self.assertEqual(self.manager.injector.inject_skin.call_args.args[0], "skin_11003")

    def test_no_favorite_falls_back_to_random(self):
        self.service.preferences.snapshot.return_value = {"excluded": [], "favorites": {}, "automatic": "favorites"}
        self.manager._run_injection.side_effect = self.execute
        self.manager.injector.inject_skin.side_effect = lambda *a, **k: self.manager.arena_overlay_ready()
        self.run_prepare()
        self.process.terminate.assert_called_once()

    def test_no_stable_match_id_does_not_close(self):
        del self.game["gameData"]["gameId"]
        self.run_prepare()
        self.process.terminate.assert_not_called()

    def test_dodge_or_other_mode_disarms(self):
        self.state.current_game_mode = "ARAM"
        self.controller.observe(self.session)
        self.assertFalse(self.controller.armed)

    def test_live_api_matches_active_player_not_first_player(self):
        self.game["gameData"]["teamOne"][0]["championId"] = -3

        def get(uri):
            if uri.endswith("/lol-gameflow/v1/session"):
                return self.game
            if uri.endswith("/current-summoner"):
                return {"puuid": "me"}
            if uri.endswith("/champion-summary.json"):
                return [{"id": 11, "alias": "MasterYi"}, {"id": 22, "alias": "Ashe"}]

        self.lcu.get.side_effect = get
        http = Mock()
        response = Mock()
        http.get.return_value.__enter__ = Mock(return_value=response)
        http.get.return_value.__exit__ = Mock(return_value=False)
        response.json.return_value = {
            "activePlayer": {"riotId": "Me#BR"},
            "allPlayers": [
                {"riotId": "Other#BR", "rawChampionName": "game_character_displayname_Ashe"},
                {"riotId": "Me#BR", "rawChampionName": "game_character_displayname_MasterYi"},
            ],
        }
        self.manager._run_injection.side_effect = self.execute
        self.manager.injector.inject_skin.side_effect = lambda *a, **k: self.manager.arena_overlay_ready()
        with patch("friends.arena_bravery.requests.Session") as factory:
            factory.return_value.__enter__.return_value = http
            self.run_prepare()
        self.assertEqual(self.manager.injector.inject_skin.call_args.kwargs["champion_id"], 11)

    def test_reconnect_failure_is_bounded_and_does_not_repeat_kill(self):
        self.manager._run_injection.side_effect = self.execute
        self.lcu.reconnect_game.return_value = False
        self.manager.injector.inject_skin.side_effect = lambda *a, **k: self.manager.arena_overlay_ready()
        counter = iter(range(0, 500, 2))
        with (
            patch("friends.arena_bravery.time.monotonic", side_effect=lambda: next(counter)),
            patch("friends.arena_bravery.time.sleep"),
        ):
            self.controller.started = 1
            self.run_prepare()
        self.process.terminate.assert_called_once()
        self.assertLess(self.lcu.reconnect_game.call_count, 15)
        self.manager.report_match_issue.assert_called()

    def test_transient_reconnect_error_is_retried(self):
        self.manager._run_injection.side_effect = self.execute
        self.lcu.reconnect_game.side_effect = [requests.ConnectionError("temporary"), True]
        self.manager.injector.inject_skin.side_effect = lambda *a, **k: self.manager.arena_overlay_ready()
        with patch("friends.arena_bravery.time.sleep"):
            self.run_prepare()
        self.assertEqual(self.lcu.reconnect_game.call_count, 2)
        self.process.terminate.assert_called_once()
