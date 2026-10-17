"""Synthetic inventories derived from Riot's documented schema; no player data."""
from copy import deepcopy
import threading
import unittest
from unittest.mock import Mock

from sexo2.overlay.gold import GoldError, GoldFeed, LiveClient, inventory, parse
from sexo2.overlay.runtime import OverlayRuntime
from tests.test_build_workflow import FakeLCU


def item(price, count=1, slot=0):
    return {'itemID': 1001 + slot, 'price': price, 'count': count, 'slot': slot}


def sample():
    return [
        {'championName': 'Ahri', 'team': 'ORDER', 'position': 'MIDDLE', 'riotId': 'synthetic-local',
         'items': [item(3000), item(50, 2, 1)]},
        {'championName': 'Annie', 'team': 'CHAOS', 'position': 'MIDDLE', 'riotId': 'synthetic-opponent',
         'items': [item(2500)]},
        {'championName': 'Jinx', 'team': 'CHAOS', 'position': 'BOTTOM', 'riotId': 'synthetic-other',
         'items': [item(4000)]},
    ]


def snapshot(players=None, game_time=120, mode='ranked'):
    game = {'mapNumber': 11, 'gameMode': 'SWIFTPLAY' if mode == 'swiftplay' else 'CLASSIC', 'gameTime': game_time}
    return parse('synthetic-local', sample() if players is None else players, game, game, mode)


class InventoryTests(unittest.TestCase):
    def test_price_quantity_empty_and_free_items(self):
        self.assertEqual(inventory([item(3000), item(50, 2, 1), item(0, 0, 6)]), 3100)
        self.assertEqual(inventory([]), 0)

    def test_incomplete_inventory_never_returns_partial_sum(self):
        for bad in [None, {}, [item(1)] * 8, [item(3000), {}],
                    [dict(item(1), price=True)], [item(float('nan'))], [item(-1)],
                    [item(10, 0)], [item(10, -1)], [dict(item(1), count=True)],
                    [dict(item(1), slot=True)], [item(100), item(200)], [item(0.5)]]:
            with self.subTest(bad=bad): self.assertIsNone(inventory(bad))

    def test_normalization_keeps_champions_not_identity_and_does_not_total_teams(self):
        value = snapshot()
        self.assertEqual(value.own.value, 3100)
        self.assertEqual(value.enemies[0].champion, 'Annie')
        self.assertNotIn('synthetic-', repr(value))
        self.assertFalse(hasattr(value, 'total_gold'))

    def test_duplicate_local_identity_champions_or_teams_fail(self):
        for rows in [sample()[1:], sample()+[sample()[0]],
                     [dict(sample()[0], team='UNKNOWN')],
                     [dict(p, riotId='synthetic-local') for p in sample()]]:
            with self.assertRaises(GoldError):snapshot(rows)
        game={'mapNumber':11, 'gameMode':'CLASSIC', 'gameTime':10}
        for after in [dict(game, gameTime=1), dict(game, mapNumber=12), dict(game, gameMode='CHERRY')]:
            with self.assertRaises(GoldError):parse('synthetic-local',sample(),game,after,'ranked')


class FeedTests(unittest.TestCase):
    def setUp(self):
        self.now=0
        self.client=Mock()
        self.client.sample.return_value=snapshot()
        self.feed=GoldFeed(client_factory=lambda:self.client, clock=lambda:self.now)
        self.context=('first', 'ranked')
        self.addCleanup(self.feed.close)

    def test_role_then_manual_opponent_and_rate_limit(self):
        self.feed.refresh(self.context)
        card=self.feed.card(self.context)
        self.assertIn('Annie',str(card)); self.assertIn('+600 G',str(card))
        for _ in range(10):self.feed.refresh(self.context)
        self.client.sample.assert_called_once_with('ranked')
        self.assertTrue(self.feed.cycle(self.context))
        self.assertIn('Jinx',str(self.feed.card(self.context)))
        self.assertIn('-900 G',str(self.feed.card(self.context)))
        self.assertNotIn('synthetic-',str(self.feed.card(self.context)))

    def test_missing_role_does_not_guess_order_from_playerlist(self):
        self.client.sample.return_value=snapshot([dict(p, position='') for p in reversed(sample())])
        self.feed.refresh(self.context)
        self.assertIn('não identificado por rota',str(self.feed.card(self.context)))
        self.assertNotIn('Diferença',str(self.feed.card(self.context)))
        self.assertTrue(self.feed.cycle(self.context))
        self.assertIn('seleção manual',str(self.feed.card(self.context)))

    def test_missing_price_unavailable_not_zero_and_failure_expires(self):
        rows=sample();rows[1]['items']=[{'itemID':3000,'slot':0,'count':1}]
        self.client.sample.return_value=snapshot(rows)
        self.feed.refresh(self.context)
        self.assertIn('Diferença em itens: indisponível',str(self.feed.card(self.context)))
        self.now=2;self.client.sample.side_effect=TimeoutError('DO_NOT_ECHO')
        self.feed.refresh(self.context)
        self.assertEqual(self.feed.diagnostic(),'unavailable')
        self.assertNotIn('Annie',str(self.feed.card(self.context)))
        self.assertNotIn('DO_NOT_ECHO',str(self.feed.card(self.context)))
        self.feed.refresh(self.context);self.assertEqual(self.client.sample.call_count,2)

    def test_game_clock_reset_invalidates_context_until_next_match(self):
        self.feed.refresh(self.context)
        self.now=2;self.client.sample.return_value=snapshot(game_time=1)
        self.feed.refresh(self.context)
        self.assertNotIn('Annie',str(self.feed.card(self.context)))
        self.now=30;self.client.sample.return_value=snapshot(game_time=200)
        self.feed.refresh(self.context)
        self.assertEqual(self.client.sample.call_count,2)
        self.feed.refresh(('new-match','ranked'))
        self.assertIn('Annie',str(self.feed.card(('new-match','ranked'))))

    def test_ttl_context_changes_clear_and_stop_reject_late_results(self):
        self.feed.refresh(self.context)
        self.now=6
        self.assertNotIn('Annie',str(self.feed.card(self.context)))
        self.assertFalse(self.feed.cycle(self.context))
        self.assertNotIn('Annie',str(self.feed.card(('other','ranked'))))
        entered,release=threading.Event(),threading.Event()
        def slow(mode):entered.set();release.wait(1);return snapshot()
        self.client.sample.side_effect=slow
        thread=threading.Thread(target=lambda:self.feed.refresh(('other','ranked')))
        thread.start();self.assertTrue(entered.wait(1))
        self.feed.close();release.set();thread.join(1)
        self.assertFalse(thread.is_alive())
        self.assertNotIn('Annie',str(self.feed.card(('other','ranked'))))

    def test_runtime_swiftplay_dynamic_values_and_no_http_on_render(self):
        lcu=FakeLCU();lcu.phase='InProgress'
        lcu.game['gameData'].update(gameMode='SWIFTPLAY',queue={'id':480})
        runtime=OverlayRuntime(lcu,enabled=lambda:True,gold_factory=lambda:self.feed,clock=lambda:self.now)
        self.addCleanup(runtime.stop)
        runtime.poll()
        self.assertTrue(runtime.frame().active)
        self.assertTrue(runtime.frame().opponent_switch)
        self.assertIn('+600 G',str(runtime.frame()))
        for _ in range(20):runtime.display_frame()
        self.client.sample.assert_called_once_with('swiftplay')
        self.assertTrue(runtime.cycle_gold_opponent())
        self.assertIn('Jinx',str(runtime.frame()))
        lcu.game['gameData']['queue']={'id':1700};lcu.game['gameData']['gameMode']='CHERRY'
        runtime.poll()
        self.assertFalse(runtime.frame().opponent_switch)
        self.assertNotIn('Ouro em itens',str(runtime.frame()))
        self.assertFalse(runtime.cycle_gold_opponent())

    def test_normal_keeps_builds_and_disabled_or_failed_context_hides_item_values(self):
        lcu=FakeLCU();lcu.phase='InProgress';enabled=[True]
        runtime=OverlayRuntime(lcu,enabled=lambda:enabled[0],gold_factory=lambda:self.feed,clock=lambda:self.now)
        self.addCleanup(runtime.stop)
        runtime.poll();self.assertIn('Annie',str(runtime.frame()))
        self.now=6;self.assertNotIn('Annie',str(runtime.frame()))
        lcu.draft_request=Mock(side_effect=TimeoutError('PRIVATE'))
        runtime.poll();self.assertNotIn('Annie',str(runtime.display_frame()))
        enabled[0]=False;runtime.poll();self.assertFalse(runtime.display_frame().active)

class LiveTransportTests(unittest.TestCase):
    """Real loopback HTTPS, synthetic server. Not a running League client."""
    def setUp(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from pathlib import Path
        import json, ssl, tempfile
        from tests.test_build_https import certificate
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        cert,key=certificate(Path(self.temp.name))
        class Handler(BaseHTTPRequestHandler):
            protocol_version='HTTP/1.1'
            def log_message(self,*args):pass
            def do_GET(self):
                import time
                self.server.traffic.append((self.path,self.headers.get('Authorization'),self.headers.get('Cookie')))
                self.server.peers.add(self.client_address[1])
                game={'mapNumber':11,'gameMode':'CLASSIC','gameTime':120}
                value={'gamestats':game,'playerlist':sample(),'activeplayername':'synthetic-local'}[self.path.rsplit('/',1)[1]]
                status, body=self.server.override or (200,json.dumps(value).encode())
                if self.server.delay:time.sleep(self.server.delay)
                try:
                    self.send_response(status)
                    self.send_header('Content-Length',str(len(body)))
                    if status==302:self.send_header('Location','https://example.invalid/')
                    self.end_headers();self.wfile.write(body)
                except (BrokenPipeError,ConnectionError,ssl.SSLError):pass
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.server.daemon_threads=True
        self.server.traffic=[];self.server.peers=set();self.server.override=None;self.server.delay=0
        tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(cert,key)
        self.server.socket=tls.wrap_socket(self.server.socket,server_side=True)
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.01},daemon=True)
        self.thread.start()
        self.client=LiveClient(base='https://127.0.0.1:'+str(self.server.server_port))
        self.addCleanup(self.close)

    def close(self):
        self.client.close();self.server.shutdown();self.server.server_close();self.thread.join(1)

    def test_anonymous_reusable_transport_ignores_proxy_and_never_reads_activeplayer(self):
        import os,warnings
        from unittest.mock import patch
        with patch.dict(os.environ,{'HTTPS_PROXY':'http://127.0.0.1:1'}),warnings.catch_warnings():
            warnings.simplefilter('ignore')
            value=self.client.sample('ranked')
        self.assertEqual(value.own.value,3100)
        self.assertEqual(len(self.server.peers),1)
        self.assertEqual([r[0].rsplit('/',1)[1] for r in self.server.traffic],
                         ['gamestats','activeplayername','playerlist','gamestats'])
        self.assertTrue(all(auth is None and cookie is None for _,auth,cookie in self.server.traffic))
        self.assertFalse(self.client.session.trust_env)
        for base in ['http://127.0.0.1:2999','https://localhost:2999','https://example.com:2999','https://127.0.0.1:65536']:
            with self.assertRaises(GoldError):LiveClient(base=base)
        with self.assertRaises(GoldError):self.client.get('activeplayer',float('inf'))

    def test_http_redirect_malformed_json_oversize_and_timeout_are_not_empty_success(self):
        import warnings,time
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            for override in [(500,b'{}'),(302,b'{}'),(200,b'{bad'),(200,b'NaN'),(200,b' '*(256*1024+1))]:
                self.server.override=override
                with self.assertRaises(GoldError):self.client.sample('ranked')
            self.server.override=None;self.server.delay=1
            with self.assertRaises(GoldError):self.client.sample('ranked')
            self.server.delay=0
