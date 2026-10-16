"""Real HTTPS/JSON integration against a synthetic LCU bound only to loopback.

This tests our adapters, not Riot's schemas or a real Windows League client.
The self-signed test certificate/key are generated inside a temporary directory.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address
import json
from pathlib import Path
import ssl
import tempfile
import threading
import unittest

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from lcu.core.client import LCU
from lcu.core.lcu_api import LCUAPI
from lcu.core.lcu_connection import LCUConnection
from lolalytics import Client
from sexo2.services.builds import BuildService
from sexo2.services.draft import BuildError
from sexo2.services.loadouts import LoadoutImporter
from tests.test_build_workflow import FakeLCU, FixtureTransport, query


def certificate(root):
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'SEXO2 synthetic LCU')])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(hours=1))
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ip_address('127.0.0.1'))]), critical=False)
            .sign(key, hashes.SHA256()))
    cert_path, key_path = root / 'certificate.pem', root / 'ephemeral.key'
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                          serialization.PrivateFormat.PKCS8,
                                          serialization.NoEncryption()))
    return cert_path, key_path


class LocalLCU(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, cert_path, key_path):
        self.state = FakeLCU()
        self.traffic = []
        self.overrides = {}
        self.disconnect_after_write = False
        super().__init__(('127.0.0.1', 0), Handler)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(cert_path, key_path)
        self.socket = tls.wrap_socket(self.socket, server_side=True)


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def handle(self):
        try:
            super().handle()
        except (ConnectionError, ssl.SSLError):
            pass  # Intentional client disconnects in negative transport checks.

    def log_message(self, *args):
        pass  # Never persist request paths, credentials or synthetic account data.

    def do_GET(self): self.dispatch('GET')
    def do_POST(self): self.dispatch('POST')
    def do_PUT(self): self.dispatch('PUT')

    def dispatch(self, method):
        length = int(self.headers.get('Content-Length', 0))
        if length > 256 * 1024:
            self.send_error(413)
            return
        body = json.loads(self.rfile.read(length)) if length else None
        self.server.traffic.append((method, self.path))
        status = 200
        override = self.server.overrides.get((method, self.path))
        if override:
            status, result = override
        else:
            try:
                result = self.server.state.get(self.path) if method == 'GET' else None
                if result is None:
                    result = self.server.state.loadout_request(method, self.path, body)
                if method != 'GET' and self.server.disconnect_after_write:
                    self.close_connection = True
                    return
            except ValueError:
                status, result = 409, {'error': 'Synthetic capacity failure'}
        if isinstance(result, bytes):
            encoded = result
        elif result is None:
            status, encoded = 204, b''
        else:
            encoded = json.dumps(result, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class BuildHTTPSIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        cert_path, key_path = certificate(root)
        self.server = LocalLCU(cert_path, key_path)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={'poll_interval': .02}, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.client = LCU.__new__(LCU)
        connection = LCUConnection.__new__(LCUConnection)
        connection._lock = threading.RLock()
        connection.ok = True
        connection.base = f'https://127.0.0.1:{self.server.server_port}'
        connection.session = connection._prepare_session()
        # Verify the generated certificate; no global TLS setting is changed.
        connection.session.verify = str(cert_path)
        self.addCleanup(connection.session.close)
        self.client._connection = connection
        self.client._api = LCUAPI(connection)
        self.transport = FixtureTransport()
        self.service = BuildService(self.client, Client(transport=self.transport), risk=lambda: 'medium')
        self.addCleanup(self.service.close)
        self.importer = LoadoutImporter(self.client, root / 'loadouts.json')
        self.state = self.server.state

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def apply(self, result, entry='wr', target='runes'):
        return self.service.import_selection(dict(revision=result['revision'], resultId=result['resultId'],
                                                 entryId=entry, target=target), self.importer)

    def test_ranked_pair_and_two_opponents_roundtrip_preserve_personal_pages(self):
        self.state.session['timer']['phase'] = 'FINALIZATION'
        # Both recorded source samples use vslane=middle; don't relabel a fixture.
        self.state.session['theirTeam'][1]['assignedPosition'] = 'middle'
        personal_runes = deepcopy(self.state.pages[0])
        personal_items = deepcopy(self.state.sets['itemSets'][0])
        query(self.service)
        query(self.service, selection='matchup', opponentId=1)
        result = query(self.service, selection='matchup', opponentId=13)
        self.assertEqual({e['id'] for e in result['entries']}, {'wr', 'common', 'vs:1', 'vs:13'})
        self.assertTrue(self.apply(result, 'common')['verified'])
        self.assertTrue(self.apply(result, 'vs:13')['verified'])
        self.assertTrue(self.apply(result, 'vs:13', 'items')['verified'])
        self.assertEqual(len(self.state.pages), 2)
        self.assertEqual(self.state.pages[0]['selectedPerkIds'], personal_runes['selectedPerkIds'])
        self.assertEqual(len(self.state.pages[-1]['selectedPerkIds']), 9)
        self.assertEqual(self.state.sets['itemSets'][0], personal_items)
        managed = self.state.sets['itemSets'][1:]
        self.assertEqual(len(managed), 2)
        self.assertTrue(all(s['associatedMaps'] == [11] for s in managed))
        self.assertTrue(all(s['associatedChampions'] == [103] for s in managed))
        labels = ' '.join(b['type'] for s in managed for b in s['blocks'])
        for name in ['WR', 'Common', 'Annie', 'Ryze']:
            self.assertIn(name, labels)

    def test_aram_roundtrip_uses_current_catalog_and_map_twelve(self):
        self.state.session['myTeam'][0].update(championId=222, assignedPosition='')
        self.state.game['gameData'].update(queue={'id': 450}, gameMode='ARAM', mapId=12)
        result = query(self.service, tier='all')
        self.assertEqual({e['id'] for e in result['entries']}, {'wr', 'common'})
        self.assertTrue(self.apply(result, 'common')['verified'])
        self.assertTrue(self.apply(result, 'common', 'items')['verified'])
        self.assertEqual(self.state.sets['itemSets'][-1]['associatedMaps'], [12])
        self.assertEqual(self.state.sets['itemSets'][-1]['associatedChampions'], [222])
        self.assertEqual(len(self.state.pages[-1]['selectedPerkIds']), 9)

    def test_phase_exit_blocks_writes_even_without_a_ui_notification(self):
        result = query(self.service)
        self.state.phase = 'InProgress'
        with self.assertRaises(BuildError):
            self.apply(result)
        self.assertFalse(any(m != 'GET' for m, _ in self.server.traffic))

    def test_rejected_write_is_not_retried_and_personal_pages_remain(self):
        result = query(self.service)
        previous = deepcopy(self.state.pages)
        self.state.reject_write = True
        with self.assertRaises(BuildError):
            self.apply(result)
        self.assertEqual(self.state.pages, previous)
        self.assertEqual([m for m, _ in self.server.traffic if m != 'GET'], ['POST'])

    def test_lost_response_after_commit_is_not_success_or_automatically_retried(self):
        result = query(self.service)
        self.server.disconnect_after_write = True
        with self.assertRaises(BuildError):
            self.apply(result)
        self.assertEqual(len(self.state.pages), 2)  # Server applied it; acknowledgement was lost.
        self.assertEqual([m for m, _ in self.server.traffic if m != 'GET'], ['POST'])

    def test_readback_mismatch_is_not_reported_as_success(self):
        result = query(self.service)
        self.state.drop_write = True
        with self.assertRaisesRegex(BuildError, 'confirmada'):
            self.apply(result)

    def test_draft_http_failure_is_actionable_and_recovery_uses_fresh_data(self):
        endpoint = ('GET', '/lol-gameflow/v1/gameflow-phase')
        self.server.overrides[endpoint] = (503, {'error': 'Synthetic private details'})
        with self.assertRaises(BuildError) as error:
            self.service.context()
        self.assertNotIn('private', str(error.exception))
        self.assertFalse(self.transport.calls)
        del self.server.overrides[endpoint]
        self.client._api._cache_put(endpoint[1], 'Lobby', 60)
        self.assertTrue(self.service.context()['available'])


if __name__ == '__main__':
    unittest.main()
