import socket,unittest
from unittest.mock import AsyncMock,Mock,patch
from party.network.tunnel_connection import connect_with_dns_fallback

class TunnelDNSTests(unittest.IsolatedAsyncioTestCase):
    async def test_normal_dns_does_not_use_fallback(self):
        ws=Mock()
        with patch('party.network.tunnel_connection.websockets.connect',AsyncMock(return_value=ws)),patch('party.network.tunnel_connection._resolve_cloudflare')as resolve:
            self.assertIs(await connect_with_dns_fallback('wss://host.trycloudflare.com/room'),ws)
            resolve.assert_not_called()
    async def test_fallback_preserves_uri_and_tls_name(self):
        ws=Mock();url='wss://host.trycloudflare.com/room?access=test';tls=Mock()
        with patch('party.network.tunnel_connection.websockets.connect',AsyncMock(side_effect=[socket.gaierror(),ws]))as connect,patch('party.network.tunnel_connection._resolve_cloudflare',return_value='104.16.230.132'):
            self.assertIs(await connect_with_dns_fallback(url,ssl=tls),ws)
            args,kwargs=connect.call_args
            self.assertEqual(args,(url,));self.assertIs(kwargs['ssl'],tls)
            self.assertEqual(kwargs['host'],'104.16.230.132');self.assertEqual(kwargs['server_hostname'],'host.trycloudflare.com')
    async def test_fallback_is_limited_to_secure_quick_tunnels(self):
        for url in ['wss://other.example/room','ws://host.trycloudflare.com/room']:
            with patch('party.network.tunnel_connection.websockets.connect',AsyncMock(side_effect=socket.gaierror())),patch('party.network.tunnel_connection._resolve_cloudflare')as resolve:
                with self.assertRaises(socket.gaierror):await connect_with_dns_fallback(url)
                resolve.assert_not_called()

    async def test_verified_address_covers_temporary_dns_failure(self):
        ws = Mock(remote_address=('104.16.230.132',443))
        url = 'wss://cache-test.trycloudflare.com/room'
        with patch.dict('party.network.tunnel_connection._VERIFIED_ADDRESSES',{},clear=True), patch('party.network.tunnel_connection.websockets.connect',AsyncMock(side_effect=[ws,socket.gaierror(),ws])) as connect, patch('party.network.tunnel_connection._resolve_cloudflare') as resolve:
            await connect_with_dns_fallback(url,proxy=None)
            self.assertIs(await connect_with_dns_fallback(url,proxy=None),ws)
            resolve.assert_not_called()
            self.assertEqual(connect.call_args.kwargs['host'],'104.16.230.132')
            self.assertEqual(connect.call_args.kwargs['server_hostname'],'cache-test.trycloudflare.com')
