"""Bridge/transport tests; no real client, credentials or remote requests."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, MagicMock, patch

from lcu.core.client import LCU
from lolalytics import Client
from pengu.communication.message_handler import MessageHandler
from tests.test_build_workflow import FakeLCU, FixtureTransport
from sexo2.overlay.model import OverlayStore


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.client=LCU.__new__(LCU)
        self.session=MagicMock()
        self.client._connection=SimpleNamespace(ok=True,base='https://127.0.0.1:12345',session=self.session,
                                                _lock=threading.RLock())
        self.client._api=Mock()
        self.response=Mock(status_code=200)
        self.response.iter_content.return_value=[b'[]']
        self.session.request.return_value.__enter__.return_value=self.response

    def test_only_local_allowlisted_endpoints_and_no_write_retry(self):
        for method,path in [('DELETE','/lol-perks/v1/pages/1'),('PUT','/lol-champ-select/v1/session'),
                            ('GET','https://example.test'),('GET','/lol-item-sets/v1/item-sets/../sets')]:
            with self.subTest(method=method,path=path),self.assertRaises(ValueError):
                self.client.loadout_request(method,path)
        self.session.request.assert_not_called()
        self.session.request.side_effect=TimeoutError('SYNTHETIC PRIVATE')
        with self.assertRaises(ValueError)as error:self.client.loadout_request('POST','/lol-perks/v1/pages',{})
        self.assertNotIn('PRIVATE',str(error.exception));self.session.request.assert_called_once()

    def test_bounded_response_and_status_failure(self):
        self.assertEqual(self.client.loadout_request('GET','/lol-perks/v1/pages'),[])
        self.response.iter_content.return_value=[b'x'*(4*1024*1024+1)]
        with self.assertRaises(ValueError):self.client.loadout_request('GET','/lol-perks/v1/pages')
        self.response.status_code=429
        with self.assertRaisesRegex(ValueError,'429'):self.client.loadout_request('POST','/lol-perks/v1/pages',{})

    def test_redirects_not_followed_and_response_closed(self):
        self.client.loadout_request('GET','/lol-perks/v1/pages')
        self.assertFalse(self.session.request.call_args.kwargs['allow_redirects'])
        self.session.request.return_value.__exit__.assert_called()
        self.client._connection.base='https://example.test:1234'
        with self.assertRaises(ValueError):self.client.loadout_request('GET','/lol-perks/v1/pages')

    def test_schema_failure_cannot_become_an_empty_list(self):
        self.response.iter_content.return_value=[b'{broken']
        with self.assertRaises(ValueError):self.client.loadout_request('GET','/lol-perks/v1/pages')
        self.response.iter_content.return_value=[b'[NaN]']
        with self.assertRaises(ValueError):self.client.loadout_request('GET','/lol-perks/v1/pages')

    def test_draft_reads_are_bounded_fresh_and_allowlisted(self):
        self.client._api.get.side_effect=AssertionError('Legacy cache must not be used')
        self.response.iter_content.return_value=[b'"ChampSelect"']
        self.assertEqual(self.client.draft_request('/lol-gameflow/v1/gameflow-phase'),'ChampSelect')
        request=self.session.request.call_args
        self.assertEqual(request.kwargs['timeout'],(1,2))
        self.assertTrue(request.kwargs['stream'])
        self.assertFalse(request.kwargs['allow_redirects'])
        for path in ['/lol-summoner/v1/current-summoner','https://example.test',
                     '/lol-champ-select/v1/session/../../']:
            with self.subTest(path=path),self.assertRaises(ValueError):self.client.draft_request(path)

    def test_reconnect_does_not_mix_the_captured_session_and_endpoint(self):
        def respond(*args,**kwargs):
            self.client._connection.base='https://127.0.0.1:54321'
            self.client._connection.session=MagicMock()
            return MagicMock(__enter__=Mock(return_value=self.response))
        self.session.request.side_effect=respond
        self.client.draft_request('/lol-gameflow/v1/gameflow-phase')
        self.assertEqual(self.session.request.call_args.args[1],
                         'https://127.0.0.1:12345/lol-gameflow/v1/gameflow-phase')


class BuildBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.handler=MessageHandler.__new__(MessageHandler)
        self.handler._background_lock=threading.Lock()
        self.handler.overlay_store=OverlayStore()
        self.lcu=FakeLCU();self.handler.skin_scraper=SimpleNamespace(lcu=self.lcu)
        self.handler._send_response=Mock()
        self.client=Client(transport=FixtureTransport())
        for target,value in [('lolalytics.Client',self.client),
                             ('pengu.communication.message_handler.get_user_data_dir',Path(self.temp.name))]:
            context=patch(target,return_value=value);context.start();self.addCleanup(context.stop)
        self.addCleanup(self.handler.close_builds)
        self.handler._handle_builds({'type':'sexo2-build-context','requestId':'context-1'})
        self.wait('context-1')

    def wait(self,rid):
        until=time.monotonic()+2
        while time.monotonic()<until:
            messages=[json.loads(call.args[0])for call in self.handler._send_response.call_args_list]
            value=next((m for m in messages if m.get('requestId')==rid),None)
            if value:return value
            time.sleep(.005)
        self.fail('Bridge response timed out: '+rid)

    def test_context_does_not_wait_for_source_query(self):
        entered,release=threading.Event(),threading.Event()
        original=self.client.recommend
        def slow(*args,**kwargs):
            entered.set();release.wait(2);return original(*args,**kwargs)
        revision=self.wait('context-1')['context']['revision']
        try:
            with patch.object(self.client,'recommend',side_effect=slow):
                self.handler._handle_builds({'type':'sexo2-build-query','requestId':'query-1','revision':revision})
                self.assertTrue(entered.wait(1))
                self.handler._handle_builds({'type':'sexo2-build-context','requestId':'context-2'})
                self.assertEqual(self.wait('context-2')['type'],'sexo2-build-context-data')
                release.set();self.assertEqual(self.wait('query-1')['type'],'sexo2-build-data')
        finally:release.set()

    def test_overlay_preview_and_retry_are_explicit_and_do_not_import(self):
        runtime=Mock()
        runtime.preview.return_value=True
        runtime.retry_arena.return_value=False
        runtime.diagnostic.return_value={'code':'preview','message':'Prévia temporária.'}
        self.handler.overlay_runtime=runtime
        before=len(self.lcu.requests)
        self.handler._route('sexo2-overlay-preview',{'type':'sexo2-overlay-preview','requestId':'preview-1'})
        self.assertTrue(self.wait('preview-1')['accepted'])
        runtime.preview.assert_called_once()
        self.handler._route('sexo2-overlay-retry',{'type':'sexo2-overlay-retry','requestId':'retry-1'})
        self.assertFalse(self.wait('retry-1')['accepted'])
        self.assertEqual(len(self.lcu.requests),before)

    def test_query_then_import_reaches_real_services_with_fake_lcu(self):
        revision=self.wait('context-1')['context']['revision']
        self.handler._route('sexo2-build-query',{'type':'sexo2-build-query','requestId':'query-1','revision':revision})
        response=self.wait('query-1')
        self.assertEqual(response['type'],'sexo2-build-data')
        self.assertIn('8992',response['result']['runeNames'])
        self.handler._route('sexo2-build-select',{'type':'sexo2-build-select','requestId':'select-1',
            'revision':revision,'resultId':response['result']['resultId'],'entryId':'common'})
        self.assertTrue(self.wait('select-1')['result']['selected'])
        self.assertEqual(self.handler.overlay_store._data['selected'],1)
        self.handler._handle_builds({'type':'sexo2-build-import','requestId':'import-1',
            'revision':revision,'resultId':response['result']['resultId'],'entryId':'wr','target':'runes'})
        answer=self.wait('import-1')
        self.assertTrue(answer['result']['verified'])
        self.assertEqual(len(self.lcu.pages),2)

    def test_unknown_error_is_sanitized_and_close_blocks_new_work(self):
        with patch.object(self.handler._build_service,'context',side_effect=RuntimeError('SYNTHETIC PRIVATE')):
            self.handler._handle_builds({'type':'sexo2-build-context','requestId':'context-error'})
            answer=self.wait('context-error')
            self.assertNotIn('PRIVATE',json.dumps(answer))
        self.handler.close_builds();self.handler._send_response.reset_mock()
        self.handler._handle_builds({'type':'sexo2-build-context','requestId':'after-close'})
        self.handler._send_response.assert_not_called()

    def test_invalid_correlation_id_does_not_enqueue_work(self):
        self.handler._send_response.reset_mock()
        self.handler._handle_builds({'type':'sexo2-build-context','requestId':{'bad':'value'}})
        self.handler._send_response.assert_not_called()


if __name__=='__main__':unittest.main()
