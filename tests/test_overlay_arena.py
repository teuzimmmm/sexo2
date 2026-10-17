"""Arena feed against real sanitized source fixtures, without network or game."""
from copy import deepcopy
import threading
import time
import unittest
from unittest.mock import Mock

from lolalytics import Client, Query
from sexo2.overlay.arena import ArenaFeed, cards, own_champion
from sexo2.overlay.processes import ProcessCatalog
from sexo2.overlay.runtime import OverlayRuntime
from sexo2.services.draft import game_key, game_mode
from tests.test_build_workflow import FakeLCU, FixtureTransport


class ArenaOverlayTests(unittest.TestCase):
    def setUp(self):
        self.lcu = FakeLCU()
        self.transport = FixtureTransport()
        self.client = Client(transport=self.transport)
        self.feed = ArenaFeed(self.lcu, client_factory=lambda: self.client)
        self.addCleanup(self.feed.close)

    def wait(self):
        until = time.monotonic() + 3
        while self.feed._busy and time.monotonic() < until:
            time.sleep(.005)
        self.assertFalse(self.feed._busy)

    def test_actual_fixture_popularity_names_and_observation_slots(self):
        self.feed.ensure('match', 222)
        self.wait()
        view = self.feed.view('match', 222)
        self.assertEqual(len(view.cards), 7)
        self.assertIn('Todos os aprimoramentos', view.cards[0].title)
        self.assertIn('Aprimoramento 1', view.cards[1].title)
        self.assertIn('Critical Rhythm · PR 35.29% · 5130 jogos', str(view))
        self.assertNotIn("'raw'", str(view))
        self.assertNotIn('Runa principal', str(view))
        for _ in range(10):
            self.feed.ensure('match', 222)
        self.assertEqual(len(self.transport.calls), 1)

    def test_restricted_metrics_never_projected_and_missing_names_use_ids(self):
        r = self.client.recommend(Query('jinx', mode='arena'))
        for rows in r.item_rankings.values():
            for row in rows:
                row['metrics']['win_rate'] = 98.7654
                row['raw'] = {'private': 'PRIVATE'}
        value = str(cards(r, 'Jinx', {}))
        self.assertIn('Aprimoramento #1328', value)
        self.assertNotIn('98.7654', value)
        self.assertNotIn('PRIVATE', value)

    def test_failure_has_no_retry_loop_and_manual_retry_is_bounded(self):
        client = Mock()
        client.recommend.side_effect = RuntimeError('PRIVATE')
        self.feed._factory = lambda: client
        self.feed.ensure('match', 222); self.wait()
        for _ in range(10):
            self.feed.ensure('match', 222)
        self.assertEqual(client.recommend.call_count, 1)
        self.assertNotIn('PRIVATE', str(self.feed.view('match', 222)))
        self.assertIn('Reconsultar', str(self.feed.view('match', 222)))
        self.assertTrue(self.feed.retry())
        self.assertFalse(self.feed.retry())
        self.feed.ensure('match', 222); self.wait()
        self.assertEqual(client.recommend.call_count, 2)

    def test_late_source_response_is_discarded_without_queue_flood(self):
        entered, release = threading.Event(), threading.Event()
        original = self.client.recommend
        def slow(query):
            entered.set(); release.wait(2)
            return original(query)
        self.client.recommend = slow
        try:
            self.feed.ensure('first', 222)
            self.assertTrue(entered.wait(1))
            for _ in range(20):
                self.feed.ensure('next', 222)
            release.set(); self.wait()
            self.assertNotEqual(self.feed._complete, ('first', 222))
            self.assertIn('carregando', self.feed.view('next', 222).cards[0].title)
            self.feed.ensure('next', 222); self.wait()
            self.assertIn('Jinx', self.feed.view('next', 222).cards[0].title)
            self.assertEqual(len(self.transport.calls), 1)  # second request uses collector cache
        finally:
            release.set()

    def test_runtime_arena_without_draft_ui_and_no_source_for_unknown_mode(self):
        self.lcu.phase = 'InProgress'
        self.lcu.game['gameData'] = {'gameId': 10, 'queue': {'gameMode': 'CHERRY'}, 'teamOne': [{'summonerId': 100, 'championId': 222}]}
        runtime = OverlayRuntime(self.lcu, enabled=lambda: True, champion=lambda: 222,
                                 arena_factory=lambda: self.feed)
        self.addCleanup(runtime.stop)
        self.assertTrue(runtime.poll().active)
        self.assertIn('aguardando oferta', str(runtime.frame()))
        self.assertNotIn('Critical Rhythm', str(runtime.frame()))
        self.wait()
        self.assertTrue(runtime.poll().active)
        self.assertNotIn('Todos os aprimoramentos', str(runtime.frame()))
        self.lcu.game['gameData']['queue'] = {'id': 999999}
        self.assertFalse(runtime.poll().active)
        self.assertEqual(game_mode({'queue': {'gameMode': 'CHERRY'}}), 'arena')

    def test_offered_view_uses_only_current_choices_general_table_and_same_mode(self):
        from sexo2.overlay.offers import Choice, Offer
        self.feed.ensure('match', 222); self.wait()
        offer = Offer(('match', 222, 'arena'), 1, 1,
                      (Choice('1328', 'Critical Rhythm'), Choice('9999999', 'Without statistics'), Choice(None, None)))
        view = self.feed.offered_view('match', 222, offer)
        self.assertIn('Critical Rhythm ·', str(self.feed.view('match', 222)))
        self.assertIn('35.29%', str(view))
        self.assertIn('5130', str(view))
        self.assertIn('Without statistics', str(view))
        self.assertEqual(len(view.cards), 1)
        self.assertNotIn('Todos os aprimoramentos', str(view))
        self.assertEqual(self.feed.offered_view('other', 222, offer).cards, ())
        self.feed.clear()
        self.assertEqual(self.feed.offered_view('match', 222, offer).cards, ())

    def test_runtime_current_offer_expires_without_waiting_for_lcu_poll(self):
        from sexo2.overlay.offers import Choice, OfferState
        now = [0]
        class Reader:
            def __init__(self): self.state = OfferState()
            def ensure(self, context): self.context = context
            def current(self, context): return self.state.current(context, now[0])
            def clear(self): self.state.clear()
            def close(self): self.clear()
            def diagnostic(self): return 'reading'
        reader = Reader()
        self.lcu.phase = 'InProgress'
        self.lcu.game['gameData'] = {'gameId': 10, 'queue': {'gameMode': 'CHERRY'}, 'teamOne': [{'summonerId': 100, 'championId': 222}]}
        runtime = OverlayRuntime(self.lcu, enabled=lambda: True, champion=lambda: 222,
            arena_factory=lambda: self.feed, offer_reader_factory=lambda: reader, clock=lambda: now[0])
        self.addCleanup(runtime.stop)
        self.assertTrue(runtime.poll().active)
        self.wait()
        choices = (Choice('1328', 'Critical Rhythm'), Choice('999999', 'Unknown stats'), Choice(None, None))
        reader.state.observe(reader.context, choices, 0)
        now[0] = 1
        reader.state.observe(reader.context, choices, 1)
        frame = runtime.frame()
        self.assertTrue(frame.active)
        self.assertIn('35.29%', str(frame.view))
        now[0] = 3
        self.assertTrue(runtime.frame().active)
        self.assertIn('aguardando oferta', str(runtime.frame()))
        self.assertNotIn('35.29', str(runtime.frame()))
        self.lcu.game['gameData']['queue'] = {'id': 2400}
        self.assertTrue(runtime.poll().active)
        reader.state.observe(reader.context, choices, 3)
        now[0] = 4
        reader.state.observe(reader.context, choices, 4)
        mayhem = runtime.frame()
        self.assertTrue(mayhem.active)
        self.assertIn('Mayhem', str(mayhem.view))
        self.assertNotIn('35.29', str(mayhem.view))
        self.assertIn('indisponíveis', str(mayhem.view))
        self.lcu.phase = 'EndOfGame'
        runtime.poll()
        self.assertFalse(runtime.frame().active)

    def test_brave_random_pick_resolves_only_local_summoner(self):
        game = {'gameData': {'teamOne': [{'summonerId': 999, 'championId': 103},
                                       {'summonerId': 100, 'championId': 222}]}}
        self.assertEqual(own_champion(self.lcu, game, -3), 222)
        game['gameData']['teamOne'].append({'summonerId': 100, 'championId': 103})
        self.assertIsNone(own_champion(self.lcu, game, -3))
        self.assertIsNone(own_champion(self.lcu, {'gameData': {'teamOne': []}}))

    def test_process_catalog_reuses_snapshot_and_drops_stale_pids_after_error(self):
        now = [0]
        enum = Mock(side_effect=[frozenset({123}), OSError('blocked'), frozenset({456})])
        catalog = ProcessCatalog(enumerate_pids=enum, clock=lambda: now[0])
        self.assertTrue(catalog.contains(123)); self.assertTrue(catalog.contains(123))
        enum.assert_called_once()
        now[0] = 2
        with self.assertRaises(OSError):
            catalog.contains(123)
        self.assertEqual(catalog._pids, frozenset())
        self.assertFalse(catalog.contains(123))
        self.assertTrue(catalog.contains(456))

    def test_clear_and_close_cannot_republish_old_views(self):
        self.feed.ensure('match', 222); self.wait()
        self.feed.clear()
        self.assertNotIn('Jinx', str(self.feed.view('match', 222)))
        self.feed.close()
        self.assertFalse(self.feed.retry())
        self.feed.ensure('another', 222)
        self.assertNotIn('Jinx', str(self.feed.view('another', 222)))


if __name__ == '__main__':
    unittest.main()
