import asyncio
import unittest

from pengu.core.websocket_server import WebSocketServer
from utils.core.security import is_loopback_host


class LoopbackHostTests(unittest.TestCase):
    def test_accepts_the_names_plugins_use(self):
        for host in ("127.0.0.1:50000", "127.0.0.1", "localhost:50099", "LOCALHOST", "[::1]:50000", "[::1]"):
            self.assertTrue(is_loopback_host(host), host)

    def test_rejects_rebound_and_malformed_hosts(self):
        for host in (None, "", "evil.example:50000", "127.0.0.1.evil.example", "localhost:abc",
                     "[::1]x", "[::2]:50000", "127.0.0.2:50000"):
            self.assertFalse(is_loopback_host(host), host)


class BridgeHostCheckTests(unittest.TestCase):
    def setUp(self):
        self.served = []
        self.server = WebSocketServer(port=50000, http_handler=lambda path, headers: self.served.append(path))

    def request(self, headers):
        return asyncio.run(self.server._process_http_request("/i18n", headers))

    def test_rebound_host_is_refused_before_any_route(self):
        response = self.request({"Host": "attacker.example:50000"})
        self.assertEqual(response[0], 403)
        self.assertEqual(self.served, [])

    def test_missing_host_is_refused(self):
        self.assertEqual(self.request({})[0], 403)
        self.assertEqual(self.served, [])

    def test_plugin_request_reaches_the_routes(self):
        self.request({"Host": "127.0.0.1:50000", "Origin": "https://127.0.0.1:61234"})
        self.assertEqual(self.served, ["/i18n"])

    def test_foreign_origin_websocket_is_still_refused(self):
        response = self.request({"Host": "127.0.0.1:50000", "Origin": "https://attacker.example", "Upgrade": "websocket"})
        self.assertEqual(response[0], 403)


if __name__ == "__main__":
    unittest.main()
