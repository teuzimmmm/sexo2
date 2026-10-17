"""Real collector fixtures, synthetic sessions, no game, credentials or network."""
from copy import deepcopy
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import Mock, patch

from lolalytics import Client
from sexo2.overlay.model import OverlayStore, text
from sexo2.overlay.runtime import OverlayRuntime
from sexo2.services.builds import BuildService
from sexo2.services.draft import BuildError, game_key
from tests.test_build_workflow import FakeLCU, FixtureTransport


class OverlayTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.lcu = FakeLCU()
        self.enabled = True
        self.runtime = OverlayRuntime(self.lcu, enabled=lambda: self.enabled, clock=lambda: self.now)
        self.store = self.runtime.store
        self.transport = FixtureTransport()
        self.service = BuildService(self.lcu, Client(transport=self.transport), risk=lambda: 'medium', overlay=self.store)
        self.addCleanup(self.service.close)
        self.addCleanup(self.runtime.stop)
        self.context = self.service.context()
        self.result = self.service.query({'revision': self.context['revision']}, self.service.begin_query())
        self.key = game_key(10)

    def playing(self):
        self.lcu.phase = 'InProgress'
        return self.runtime.poll()

    def test_handoff_keeps_actual_prepared_pages_after_draft_invalidation(self):
        self.service.invalidate()
        frame = self.playing()
        self.assertTrue(frame.active)
        self.assertEqual(len(frame.view.cards), 2)
        self.assertIn('Ahri', frame.view.cards[0].title)
        self.assertIn('Core (conjunto observado)', '\n'.join(frame.view.cards[0].lines))
        self.assertIn('sem WR conjunta', '\n'.join(frame.view.cards[0].lines))
        self.assertEqual(frame.view.selected, 0)
        self.assertNotIn('8992', self.key)

    def test_no_source_http_or_imports_during_match_polling(self):
        calls = len(self.transport.calls)
        writes = len(self.lcu.requests)
        for _ in range(10):
            self.playing()
        self.assertEqual(len(self.transport.calls), calls)
        self.assertEqual(len(self.lcu.requests), writes)

    def test_enrichment_uses_only_current_result_and_referenced_ids(self):
        item = self.result['entries'][0]['page']['blocks'][0]['choices'][0]['identifier']
        result = dict(self.result, itemNames={item: 'Item real', 'unused': 'UNUSED'}, runeNames={'8992': 'Runa real'})
        self.store.enrich(dict(result, resultId='expired'))
        self.assertNotIn('Item real', str(self.playing()))
        self.store.enrich(result)
        output = str(self.playing())
        self.assertIn('Item real', output)
        self.assertIn('Runa real', output)
        self.assertNotIn('UNUSED', str(self.store._data))
        self.assertNotIn("'raw'", str(self.store._data))

    def test_selected_preparation_is_retained_and_expired_selection_rejected(self):
        self.service.select_overlay({'revision': self.context['revision'], 'resultId': self.result['resultId'], 'entryId': 'common'})
        self.assertEqual(self.playing().view.selected, 1)
        with self.assertRaises(BuildError):
            self.service.select_overlay({'revision': self.context['revision'], 'resultId': self.result['resultId'], 'entryId': 'wr'})

    def test_wrong_match_and_end_of_game_discard_cards(self):
        self.lcu.game['gameData']['gameId'] = 11
        frame = self.playing()
        self.assertTrue(frame.active)
        self.assertEqual(frame.view.cards, ())
        self.lcu.game['gameData']['gameId'] = 10
        self.assertEqual(self.playing().view.cards, ())
        self.store.prepare(self.context, self.result)
        self.lcu.phase = 'EndOfGame'
        self.assertFalse(self.runtime.poll().active)
        self.assertIsNone(self.store._data)

    def test_unknown_modes_never_show(self):
        for data in [{'gameId': 10, 'queue': {'id': 999999}}]:
            self.lcu.game['gameData'] = data
            self.assertFalse(self.playing().active)
            self.assertEqual(self.store.view(self.key, 'ranked').cards, ())

    def test_arena_status_without_fabricated_offers_until_champion_is_known(self):
        self.lcu.game['gameData'] = {'gameId': 10, 'queue': {'gameMode': 'CHERRY'}}
        self.assertTrue(self.playing().active)
        self.assertIn('identificando campeão', str(self.runtime.frame()))
        self.assertEqual(self.store.view(self.key, 'ranked').cards, ())

    def test_preview_is_explicit_temporary_and_independent_of_client(self):
        self.lcu.draft_request = Mock(side_effect=OSError('PRIVATE'))
        self.runtime.poll()
        self.assertEqual(self.runtime.diagnostic()['code'], 'client-unavailable')
        self.assertTrue(self.runtime.preview())
        self.assertTrue(self.runtime.frame().preview)
        self.now = 21
        self.assertFalse(self.runtime.frame().active)

    def test_standard_aram_supported_but_separated_from_sr(self):
        self.lcu.game['gameData'] = {'gameId': 10, 'queue': {'id': 450}}
        frame = self.playing()
        self.assertTrue(frame.active)
        self.assertEqual(frame.view.cards, ())
        # No silent reinterpretation of SR cards as ARAM even with the same gameId.
        self.store.prepare(dict(self.context, mode='aram'), self.result)
        self.assertEqual(len(self.playing().view.cards), 2)

    def test_failures_hide_and_same_match_reconnect_can_recover(self):
        self.assertTrue(self.playing().active)
        original = self.lcu.draft_request
        self.lcu.draft_request = Mock(side_effect=TimeoutError('PRIVATE'))
        self.assertFalse(self.runtime.poll().active)
        self.assertNotIn('PRIVATE', str(self.runtime.frame()))
        self.lcu.draft_request = original
        self.lcu.phase = 'Reconnect'
        self.assertEqual(len(self.runtime.poll().view.cards), 2)

    def test_unstable_phase_missing_identity_and_malformed_response_fail_closed(self):
        for responses in [('InProgress', self.lcu.game, 'EndOfGame'), ('InProgress', {}, 'InProgress'),
                          ('InProgress', [], 'InProgress')]:
            with patch.object(self.lcu, 'draft_request', side_effect=responses):
                self.assertFalse(self.runtime.poll().active)
        self.lcu.game['gameData']['gameId'] = True
        self.assertFalse(self.playing().active)

    def test_disabled_and_expired_observation_hide_immediately(self):
        self.assertTrue(self.playing().active)
        self.now = 9
        self.assertFalse(self.runtime.frame().active)
        self.enabled = False
        self.assertFalse(self.runtime.poll().active)
        self.enabled = True
        self.assertTrue(self.playing().active)
        self.now = 7 * 3600
        self.assertEqual(self.playing().view.cards, ())

    def test_new_draft_clears_and_text_has_no_control_characters(self):
        self.lcu.game['gameData']['gameId'] = 11
        self.runtime.poll()
        self.assertEqual(self.store.view(self.key, 'ranked').cards, ())
        self.assertEqual(text('x\n\x00\u202ey'), 'xy')

    def test_champion_or_risk_change_in_same_draft_discards_prepared_cards(self):
        self.lcu.session['myTeam'][0]['championId'] = 222
        self.service.context()
        self.assertEqual(self.store.view(self.key, 'ranked').cards, ())
        self.store.prepare(self.context, self.result)
        self.service.risk = lambda: 'high'
        self.service.context()
        self.assertEqual(self.store.view(self.key, 'ranked').cards, ())

    def test_closed_store_rejects_late_worker_publication(self):
        self.runtime.stop()
        self.store.prepare(self.context, self.result)
        self.assertEqual(self.store.view(self.key, 'ranked').cards, ())

    def test_late_trade_detected_by_existing_champion_monitor_discards_cards(self):
        self.runtime.champion = lambda: 222
        self.assertEqual(self.playing().view.cards, ())

    def test_conflicting_native_match_identifiers_hide(self):
        self.lcu.game['gameId'] = 11
        self.assertFalse(self.playing().active)

    def test_overlay_fault_does_not_break_source_query(self):
        with patch.object(self.store, 'prepare', side_effect=RuntimeError('PRIVATE')):
            with self.assertLogs('sexo2.services.builds', level='WARNING') as logs:
                result = self.service.query({'revision': self.context['revision']}, self.service.begin_query())
        self.assertEqual(len(result['entries']), 2)
        self.assertNotIn('PRIVATE', str(logs.output))

    def test_matchup_becomes_initial_overlay_suggestion(self):
        self.lcu.session['timer']['phase'] = 'FINALIZATION'
        context = self.service.context()
        result = self.service.query({'revision': context['revision'], 'selection': 'matchup', 'opponentId': 1},
                                    self.service.begin_query())
        frame = self.playing()
        self.assertIn('vs Annie', frame.view.cards[frame.view.selected].title)

    def test_shutdown_creation_failure_and_inflight_poll_do_not_keep_visible_state(self):
        factory = Mock(side_effect=RuntimeError('PRIVATE'))
        runtime = OverlayRuntime(self.lcu, enabled=lambda: True, window_factory=factory)
        with self.assertLogs('sexo2.overlay.runtime', level='WARNING') as logs:
            runtime.start()
        self.assertNotIn('PRIVATE', str(logs.output))
        runtime.stop()
        self.runtime.stop()
        self.assertFalse(self.runtime.frame().active)
        self.assertIsNone(self.store._data)

    def test_start_stop_idempotent_and_window_lifecycle(self):
        window = Mock()
        runtime = OverlayRuntime(self.lcu, enabled=lambda: True, window_factory=Mock(return_value=window))
        runtime.start(); runtime.start()
        window.start.assert_called_once()
        runtime.stop(); runtime.stop()
        self.assertFalse(runtime._thread.is_alive())


if __name__ == '__main__':
    unittest.main()
