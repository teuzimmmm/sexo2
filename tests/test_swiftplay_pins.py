"""Offline regressions: local identity, persistence, validation and preparation."""

import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from pengu.processing.swiftplay_pins import SwiftplayPins, SwiftplayPanelService, read_lobby
from pengu.processing.skin_processor import SkinProcessor
from threads.handlers.swiftplay_handler import SwiftplayHandler


class PinsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "pins.json"
        self.pins = SwiftplayPins(self.path)
        self.state = SimpleNamespace(
            swiftplay_lock=threading.Lock(),
            swiftplay_pins=self.pins,
            swiftplay_skin_tracking={},
            swiftplay_extracted_mods=[],
            current_queue_id=480,
            is_swiftplay_mode=True,
            owned_skin_ids=set(),
            swiftplay_handler=None,
        )
        self.ids = [234, 555]
        self.phase = "Lobby"
        self.queue = 480
        self.slot_skin_override = {}
        self.lcu = Mock(ok=True)

        def get(url, **kw):
            if url == "/lol-lobby/v2/lobby":
                return {
                    "gameConfig": {"queueId": self.queue},
                    "localMember": {
                        "playerSlots": [
                            {"championId": c, "skinId": self.slot_skin_override.get(c, c * 1000)} for c in self.ids
                        ]
                    },
                    "members": [{"primaryChampionId": 999}],
                }
            if url == "/lol-gameflow/v1/gameflow-phase":
                return self.phase
            if "champions/" in url:
                cid = int(url.rsplit("/", 1)[1].split(".")[0])
                return {
                    "name": str(cid),
                    "skins": [{"id": cid * 1000, "name": "Padrão"}, {"id": cid * 1000 + 1, "name": "Skin"}],
                }

        self.lcu.get.side_effect = get
        self.service = SwiftplayPanelService(self.state, self.lcu)

    def payload(self, skins=(234001, 555001)):
        return {
            "championIds": self.ids.copy(),
            "selections": [{"championId": c, "skinId": s} for c, s in zip(self.ids, skins)],
        }

    def test_persist_both_and_restart(self):
        self.service.save(self.payload())
        self.assertEqual(
            {c: p["skinId"] for c, p in SwiftplayPins(self.path).snapshot().items()}, {234: 234001, 555: 555001}
        )

    def test_reorder_is_champion_keyed(self):
        self.service.save(self.payload())
        self.ids.reverse()
        rows = self.service.snapshot()["champions"]
        self.assertEqual([r["pin"]["skinId"] for r in rows], [555001, 234001])

    def test_stale_slots_rejected(self):
        payload = self.payload()
        self.ids = [234, 1]
        with self.assertRaisesRegex(ValueError, "mudaram"):
            self.service.save(payload)
        self.assertFalse(self.path.exists())

    def test_other_mode_and_brawl_rejected(self):
        for queue in [420, 450, 2300, None]:
            self.queue = queue
            self.assertIsNone(read_lobby(self.lcu))
            self.assertFalse(self.service.snapshot()["active"])
            with self.assertRaises(ValueError):
                self.service.save(self.payload())

    def test_only_local_slots(self):
        self.assertEqual(read_lobby(self.lcu), [234, 555])

    def test_queue_or_ready_check_cannot_save(self):
        for phase in ["Matchmaking", "ReadyCheck", "InProgress"]:
            self.phase = phase
            with self.assertRaises(ValueError):
                self.service.save(self.payload())

    def test_invalid_skin_is_atomic(self):
        with self.assertRaises(ValueError):
            self.service.save(self.payload((234001, 234001)))
        self.assertEqual(self.pins.snapshot(), {})

    def test_remove_does_not_touch_other_champion(self):
        self.service.save(self.payload())
        self.service.save(self.payload((None, 555001)))
        self.assertNotIn(234, self.pins.snapshot())
        self.assertIn(555, self.pins.snapshot())
        self.assertNotIn(234, self.state.swiftplay_skin_tracking)

    def test_corrupt_file_is_preserved(self):
        self.path.write_text("bad", encoding="utf-8")
        pins = SwiftplayPins(self.path)
        with self.assertRaises(ValueError):
            pins.save({234: {"skinId": 234001, "name": "Skin"}})
        self.assertEqual(self.path.read_text(), "bad")

    def test_disk_failure_does_not_update_memory(self):
        with patch("pengu.processing.swiftplay_pins.os.replace", side_effect=OSError("disk")):
            with self.assertRaises(OSError):
                self.service.save(self.payload())
        self.assertEqual(self.pins.snapshot(), {})
        self.assertEqual(self.state.swiftplay_skin_tracking, {})

    def test_hover_reset_cannot_override_pin(self):
        self.service.save(self.payload())
        processor = SkinProcessor(self.state, skin_mapping=Mock())
        processor.skin_mapping.find_skin_id_by_name.return_value = 234000
        processor._process_swiftplay_skin_name("Padrão")
        self.assertEqual(self.state.swiftplay_skin_tracking[234], 234001)

    def test_force_uses_pin_even_if_owned(self):
        self.service.save(self.payload())
        self.state.owned_skin_ids = {234001}
        handler = SwiftplayHandler(self.lcu, self.state)
        self.state.swiftplay_skin_tracking = {234: 234000}
        handler.force_base_skins_if_needed()
        tracked, owned = self.lcu.force_swiftplay_base_skins.call_args.args
        self.assertEqual(tracked, {234: 234001, 555: 555001})
        self.assertNotIn(234001, owned)

    def test_swap_refreshes_even_when_tracking_keys_unchanged(self):
        self.service.save(self.payload())
        handler = SwiftplayHandler(self.lcu, self.state)
        handler._last_sync_active_ids = frozenset([234, 555])
        self.ids = [234, 1]
        handler._sync_tracking_with_lobby()
        self.assertNotIn(555, self.state.swiftplay_skin_tracking)

    def test_prepare_uses_fresh_ids_and_pins(self):
        self.service.save(self.payload())
        injector = Mock()
        zip_path = Path(self.temp.name) / "skin.zip"
        zip_path.touch()
        injector._resolve_zip.return_value = zip_path
        injector._extract_zip_to_mod.side_effect = lambda _: Path("skinmod")
        manager = Mock(injector=injector)
        handler = SwiftplayHandler(self.lcu, self.state, manager)
        handler._last_sync_active_ids = frozenset([999])
        self.state.swiftplay_skin_tracking = {234: 234000, 999: 999001}
        handler.trigger_swiftplay_injection()
        self.assertEqual(set(handler._last_injected_tracking), {234, 555})
        self.assertEqual(handler._last_injected_tracking[234], 234001)
        self.assertEqual(len(self.state.swiftplay_extracted_mods), 2)

    def test_wrong_base_slot_blocks_preparation(self):
        self.service.save(self.payload())
        self.slot_skin_override[234] = 234002
        manager = Mock()
        handler = SwiftplayHandler(self.lcu, self.state, manager)
        handler.trigger_swiftplay_injection()
        manager.injector._resolve_zip.assert_not_called()
        self.assertFalse(self.state.swiftplay_extracted_mods)
        self.assertEqual(self.state.swiftplay_pin_status[234]["state"], "error")

    def test_explicit_default_requires_no_mod(self):
        self.service.save(self.payload((234000, 555000)))
        manager = Mock()
        handler = SwiftplayHandler(self.lcu, self.state, manager)
        handler.trigger_swiftplay_injection()
        manager.injector._resolve_zip.assert_not_called()
        self.assertEqual(self.state.swiftplay_pin_status[234]["state"], "ready")

    def test_missing_skin_shows_error(self):
        self.service.save(self.payload())
        manager = Mock()
        manager.injector._resolve_zip.return_value = None
        handler = SwiftplayHandler(self.lcu, self.state, manager)
        handler.trigger_swiftplay_injection()
        self.assertFalse(self.state.swiftplay_extracted_mods)
        self.assertEqual(self.state.swiftplay_pin_status[234]["state"], "error")


if __name__ == "__main__":
    unittest.main()
