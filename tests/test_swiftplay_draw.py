"""Swiftplay: a champion with no choice gets a drawn skin for this match only, never stored as a choice."""

import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pengu.processing.swiftplay_pins import SwiftplayPanelService, SwiftplayPins
from threads.handlers.swiftplay_handler import SwiftplayHandler


class SwiftplayDrawTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pins_path = Path(self.temp.name) / "pins.json"
        self.state = SimpleNamespace(
            swiftplay_lock=threading.Lock(),
            swiftplay_pins=SwiftplayPins(self.pins_path),
            swiftplay_skin_tracking={},
            swiftplay_extracted_mods=[],
            swiftplay_pin_status={},
            current_queue_id=480,
            is_swiftplay_mode=True,
            owned_skin_ids=set(),
            swiftplay_handler=None,
        )
        self.ids = [234, 555]
        self.lcu = Mock(ok=True)

        def get(url, **kw):
            if url == "/lol-lobby/v2/lobby":
                return {
                    "gameConfig": {"queueId": 480},
                    "localMember": {"playerSlots": [{"championId": c, "skinId": c * 1000} for c in self.ids]},
                    "members": [{"primaryChampionId": 999}],
                }
            if url == "/lol-gameflow/v1/gameflow-phase":
                return "Lobby"

        self.lcu.get.side_effect = get
        service = Mock()
        service.preferences.error = None
        service.preferences.snapshot.return_value = {"excluded": [], "favorites": {"234": [234002]}}
        service.owned.return_value = set()
        service.available.return_value = True
        service.archive.return_value = True
        service.recents.return_value = []
        service.catalogs.catalog.side_effect = lambda cid: {
            "skins": [{"skinId": cid * 1000 + n, "name": f"Skin {n}"} for n in (0, 1, 2)]
        }
        self.service = service
        self.state.friends_service = service
        self.handler = SwiftplayHandler(self.lcu, self.state)

    def test_unchosen_champions_are_drawn_with_their_favorites(self):
        with patch("friends.skin_selector.select_skin", side_effect=lambda skins, **kw: skins[0]) as select:
            picks = self.handler._draw_candidates(self.ids, {})
        self.assertEqual(set(picks), {234, 555})
        favorites = {call.args[0][0]["skinId"] // 1000: call.kwargs["favorites"] for call in select.call_args_list}
        self.assertEqual(favorites, {234: {234002}, 555: set()})

    def test_pinned_champion_is_not_drawn_and_a_client_choice_prevails(self):
        pins = {234: {"skinId": 234001, "name": "Skin 1"}}
        picks = self.handler._draw_candidates(self.ids, pins)
        self.assertEqual(set(picks), {555})
        self.state.swiftplay_skin_tracking = {555: 555002}  # chosen directly in the client
        self.handler._apply_drawn_skins(picks)
        self.assertEqual(self.state.swiftplay_skin_tracking[555], 555002)
        self.assertEqual(self.handler._drawn, {})

    def test_user_changed_champion_is_left_alone(self):
        self.handler.mark_champion_changed(555)
        self.assertEqual(set(self.handler._draw_candidates(self.ids, {})), {234})

    def test_owned_skins_are_not_drawn_because_the_client_would_apply_them(self):
        self.service.owned.return_value = {234001, 234002, 555001, 555002}
        self.service.available.side_effect = lambda cid, sid: sid not in self.service.owned.return_value
        self.assertEqual(self.handler._draw_candidates(self.ids, {}), {})

    def test_draw_is_never_a_pin_or_a_historic_entry(self):
        picks = {234: 234001, 555: 555002}
        self.state.swiftplay_skin_tracking = {234: 234000, 555: 555000}
        self.handler._apply_drawn_skins(picks)
        self.assertEqual(self.state.swiftplay_skin_tracking, picks)
        self.service.record.assert_any_call(234, 234001)
        self.assertFalse(self.pins_path.exists())
        self.assertEqual(self.state.swiftplay_handler, None)
        self.handler._last_injected_tracking = dict(picks)
        with patch("threads.handlers.swiftplay_handler.write_historic_entry") as write:
            self.handler._remember_injected_skins()
        write.assert_not_called()

    def test_trigger_injects_the_draw_and_stores_no_pin(self):
        zip_path = Path(self.temp.name) / "skin.zip"
        zip_path.touch()
        injector = Mock()
        injector._resolve_zip.return_value = zip_path
        injector._extract_zip_to_mod.side_effect = lambda _: Path("skinmod")
        handler = SwiftplayHandler(self.lcu, self.state, Mock(injector=injector))
        self.state.swiftplay_skin_tracking = {234: 234000, 555: 555000}
        with patch("threads.handlers.swiftplay_handler.get_historic_skin_for_champion", return_value=None):
            handler.trigger_swiftplay_injection()
        self.assertEqual(set(handler._last_injected_tracking), {234, 555})
        self.assertTrue(all(sid % 1000 != 0 for sid in handler._last_injected_tracking.values()))
        self.assertEqual(handler._drawn, handler._last_injected_tracking)
        self.assertEqual(SwiftplayPins(self.pins_path).snapshot(), {})

    def test_only_swiftplay_draws(self):
        self.state.current_queue_id = 420
        handler = SwiftplayHandler(self.lcu, self.state, Mock())
        self.state.swiftplay_skin_tracking = {234: 234000}
        handler.trigger_swiftplay_injection()
        self.assertEqual(handler._drawn, {})

    def test_catalog_keeps_the_rarity_the_client_reports(self):
        lcu = Mock()
        lcu.get.return_value = {
            "name": "Ahri",
            "skins": [
                {
                    "id": 103001,
                    "name": "Dinastia",
                    "rarity": "kEpic",
                    "chromas": [{"id": 103010, "name": "Rubi", "rarities": [{"region": "riot", "rarity": 2}]}],
                },
                {"id": 103002, "name": "Sem raridade"},
            ],
        }
        skins = SwiftplayPanelService(self.state, lcu).catalog(103)["skins"]
        by_id = {s["skinId"]: s for s in skins}
        self.assertEqual(by_id[103001]["rarity"], "kEpic")
        self.assertEqual(by_id[103010]["chromaRarity"], 2)
        self.assertIsNone(by_id[103002]["rarity"])


if __name__ == "__main__":
    unittest.main()
