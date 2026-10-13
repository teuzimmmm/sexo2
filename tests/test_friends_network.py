import asyncio,unittest,secrets
from types import SimpleNamespace
from unittest.mock import patch
from tests import test_friends_features as fixtures
from party.hosting.friends_relay import FriendsRelay
from party.core.party_manager import PartyManager

class CoordinatedNetworkTests(unittest.IsolatedAsyncioTestCase):
    async def test_two_real_clients_coordinate_and_optout_is_respected(self):
        first=fixtures.ServiceTests();second=fixtures.ServiceTests();first.setUp();second.setUp()
        self.addCleanup(first.doCleanups);self.addCleanup(second.doCleanups)
        second.ids=[22];second.state.locked_champ_id=22;second.state.last_hovered_skin_id=22001
        first.state._test_sid=1;second.state._test_sid=2
        for case in [first,second]:case.state.phase='ChampSelect';case.state.friends_service=case.service;case.state.friends_event_loop=asyncio.get_running_loop()
        relay=FriendsRelay(secrets.token_urlsafe(32));port=await relay.start();self.addAsyncCleanup(relay.close)
        def matcher(lcu,state):return SimpleNamespace(get_my_summoner_id=lambda:state._test_sid,get_my_summoner_name=lambda:f'Test {state._test_sid}',get_all_summoner_ids=lambda:{1,2},get_team_info=lambda:({1:11,2:22},{11,22}))
        with patch('party.core.party_manager.LobbyMatcher',side_effect=matcher),patch('party.network.ws_relay.relay_settings',return_value=(f'ws://127.0.0.1:{port}',relay.token)):
            a=PartyManager(first.lcu,first.state);b=PartyManager(second.lcu,second.state);first.state.party_manager=a;second.state.party_manager=b
            self.addAsyncCleanup(a.disable);self.addAsyncCleanup(b.disable)
            await a.enable();await b.enable()
            for _ in range(50):
                if all(len(r.members)==2 for manager in [a,b]for r in manager._relays.values()):break
                await asyncio.sleep(.02)
            await asyncio.to_thread(first.service.handle,{'action':'lottery-optin','enabled':True})
            await asyncio.to_thread(second.service.handle,{'action':'lottery-optin','enabled':True})
            await asyncio.to_thread(first.service.handle,{'action':'lottery-start','theme':'PROJETO'})
            for _ in range(60):
                await asyncio.to_thread(second.service.snapshot)
                if second.state.historic_skin_id==22002:break
                await asyncio.sleep(.03)
            self.assertEqual(first.state.historic_skin_id,11002);self.assertEqual(second.state.historic_skin_id,22002)
            self.assertTrue(second.service.draw_result['success'])
            await asyncio.to_thread(second.service.handle,{'action':'lottery-optin','enabled':False})
            count=second.lcu.set_my_selection_skin.call_count
            await asyncio.to_thread(first.service.handle,{'action':'lottery-start','theme':'Arcane'})
            for _ in range(6):await asyncio.sleep(.04);await asyncio.to_thread(second.service.snapshot)
            self.assertEqual(first.state.historic_skin_id,11001);self.assertEqual(second.state.historic_skin_id,22002)
            self.assertEqual(second.lcu.set_my_selection_skin.call_count,count)
            await a.disable();await b.disable()
