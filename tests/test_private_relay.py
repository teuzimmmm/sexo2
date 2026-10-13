import asyncio,json,secrets,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode
from websockets.asyncio.client import connect
from websockets.exceptions import InvalidStatus
from party.hosting.friends_relay import FriendsRelay
from party.network.ws_relay import PartyRelay
from party.network.private_server_config import parse_server_link,save_server_link

async def until(predicate):
    for _ in range(100):
        if predicate():return
        await asyncio.sleep(.02)
    raise AssertionError('Relay did not deliver the expected state')

class LinkTests(unittest.TestCase):
    def test_link_roundtrip_and_public_default(self):
        token=secrets.token_urlsafe(32)
        self.assertEqual(parse_server_link('https://some-host.trycloudflare.com/#rose='+token),('wss://some-host.trycloudflare.com',token))
        self.assertTrue(parse_server_link('')[0].startswith('wss://'))
    def test_rejects_invalid_or_unsafe_links(self):
        for link in ['file:///c:/test','http://host','https://user:pass@host','https://host/a','https://host/?x=1','https://host/#rose=short']:
            with self.subTest(link=link),self.assertRaises(ValueError):parse_server_link(link)
    def test_config_preserves_preferences_and_room(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'config.ini';p.write_text('[General]\nleaguepath=C:\\100%\\Game\n[Party]\nroom_key=my-old-room\n',encoding='utf-8')
            with patch('config.get_config_file_path',return_value=p):save_server_link('https://host.trycloudflare.com/#rose='+'a'*43)
            data=p.read_text(encoding='utf-8')
            self.assertIn('my-old-room',data);self.assertIn('100%',data);self.assertIn('relay_access',data)

class PrivateRelayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.token=secrets.token_urlsafe(32);self.server=FriendsRelay(self.token)
        port=await self.server.start();self.base=f'ws://127.0.0.1:{port}'
        self.addAsyncCleanup(self.server.close)
    def url(self,key='friends-test-room',token=None):
        return self.base+'/room?'+urlencode({'key':key,'access':token if token is not None else self.token,'v':'1.4.7'})
    async def test_wrong_token_refused_and_unicode_safe(self):
        for token in ['wrong','☃']:
            with self.assertRaises(InvalidStatus) as e:await connect(self.url(token=token))
            self.assertEqual(e.exception.response.status_code,403)
    async def test_real_rose_clients_exchange_skins_and_leave(self):
        with patch('party.network.ws_relay.relay_settings',return_value=(self.base,self.token)):
            a=PartyRelay('friends-test-room',1,'Test A');b=PartyRelay('friends-test-room',2,'Test B')
            self.addAsyncCleanup(a.disconnect);self.addAsyncCleanup(b.disconnect)
            self.assertTrue(await a.connect());self.assertTrue(await b.connect())
            await until(lambda:len(a.members)==2 and len(b.members)==2)
            await a.send_state({'champion_id':11,'skin_id':11001})
            await b.send_state({'champion_id':22,'skin_id':22002})
            await until(lambda:any(m.get('skin',{}).get('skin_id')==22002 for m in a.members) and any(m.get('skin',{}).get('skin_id')==11001 for m in b.members))
            await b.disconnect();await until(lambda:len(a.members)==1)
    async def test_rooms_are_isolated(self):
        async with connect(self.url())as a,connect(self.url(key='another-test-room'))as b:
            await a.recv();await b.recv()
            await a.send(json.dumps({'type':'join','summoner_id':1,'summoner_name':'A'}));await a.recv()
            await b.send(json.dumps({'type':'join','summoner_id':2,'summoner_name':'B'}))
            msg=json.loads(await b.recv());self.assertEqual([m['summoner_id']for m in msg['members']],[2])
    async def test_rejoin_replaces_same_player(self):
        async with connect(self.url())as a:
            await a.recv();await a.send(json.dumps({'type':'join','summoner_id':1}));await a.recv()
            async with connect(self.url())as b:
                await b.recv();await b.send(json.dumps({'type':'join','summoner_id':1}));msg=json.loads(await b.recv())
                self.assertEqual(len(msg['members']),1);await a.wait_closed();self.assertEqual(a.close_reason,'replaced')
    async def test_capacity_refused(self):
        self.server.max_members=1
        async with connect(self.url())as a:
            with self.assertRaises(InvalidStatus)as e:await connect(self.url())
            self.assertEqual(e.exception.response.status_code,409)
    async def test_invalid_member_and_skin_rejected(self):
        async with connect(self.url())as a:
            await a.recv();await a.send(json.dumps({'type':'join','summoner_id':True}));await a.wait_closed();self.assertEqual(a.close_code,1008)
        with self.assertRaises(ValueError):FriendsRelay.skin({'skin_id':'bad'})
