"""End-to-end automatic items: real source fixtures, synthetic local client."""
from copy import deepcopy
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock

from lolalytics import Client, Query
from lolalytics.errors import TransportError
from sexo2.services.auto_items import AutoItems, ItemPlans
from sexo2.services.loadouts import LoadoutImporter
from sexo2.overlay.runtime import OverlayRuntime
from sexo2.sources.mayhem import MayhemClient
from tests.test_build_workflow import FakeLCU, FixtureTransport, query, service
from tests.test_mode_sources import DATA

class AutoItemsTests(unittest.TestCase):
    def setUp(self):
        self.lcu=FakeLCU();self.plans=ItemPlans();self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.importer=LoadoutImporter(self.lcu,Path(self.tmp.name)/'owned.json')
        self.transport=FixtureTransport();self.client=Client(transport=self.transport)
        self.auto=AutoItems(self.lcu,plans=self.plans,importer=self.importer,client_factory=lambda:self.client)
        self.addCleanup(self.auto.close)
        original=self.lcu.loadout_request
        def catalog(method,path,payload=None):
            result=original(method,path,payload)
            if method=='GET' and path.endswith('/items.json'):
                from tests.test_mode_sources import source
                result+=source('items-extra.json')
            return result
        self.lcu.loadout_request=catalog
        self.personal=deepcopy(self.lcu.sets['itemSets'][0])

    def wait(self):
        until=time.monotonic()+5
        while self.auto._busy and time.monotonic()<until:time.sleep(.005)
        self.assertFalse(self.auto._busy)

    def apply(self):
        self.auto.tick();self.wait()
        self.assertEqual(self.auto.diagnostic()['code'],'imported')
        self.assertEqual(self.lcu.sets['itemSets'][0],self.personal)
        self.assertLessEqual(len(self.lcu.sets['itemSets']),3)
        self.assertFalse(any('/lol-perks/' in p for m,p,_ in self.lcu.requests if m!='GET'))

    def test_normal_and_ranked_import_items_without_opening_panel_and_only_once(self):
        self.lcu.game['gameData']['queue']['id']=400
        self.apply();first=deepcopy(self.lcu.sets)
        for _ in range(4):self.auto.tick()
        self.assertEqual(first,self.lcu.sets)
        self.assertEqual(len(self.transport.calls),3)
        self.assertEqual(self.lcu.sets['itemSets'][-1]['associatedMaps'],[11])

    def test_aram_auto_import_uses_real_aram_source_and_has_no_draft_panel_dependency(self):
        self.lcu.game['gameData'].update(queue={'id':450},gameMode='ARAM',mapId=12)
        self.lcu.session['myTeam'][0]['championId']=222
        self.apply()
        self.assertTrue(all('/aram/' in url for url in self.transport.calls))
        self.assertEqual(self.lcu.sets['itemSets'][-1]['associatedMaps'],[12])
        self.assertEqual(self.lcu.sets['itemSets'][-1]['associatedChampions'],[222])

    def test_exact_pages_prepared_in_panel_are_handed_to_background_without_requery(self):
        s=service(self.lcu)[0];self.addCleanup(s.close);s.item_plans=self.plans
        result=query(s);self.assertEqual(self.plans.version,1)
        self.apply();self.assertEqual(self.transport.calls,[])
        labels=str(self.lcu.sets)
        self.assertIn(str(result['entries'][0]['page']['core_metrics']['games']),labels)
        self.assertIn('Common',labels)

    def test_swift_lobby_two_real_champion_choices_share_the_two_set_budget(self):
        # Use the same real champion twice to test dedup, then two distinct groups
        # through the importer itself (no relabelled source fixture).
        self.lcu.phase='Lobby'
        lobby={'gameConfig':{'queueId':480},'localMember':{'playerSlots':[{'championId':103},{'championId':222}]}}
        original=self.lcu.draft_request
        self.lcu.draft_request=lambda p:deepcopy(lobby) if p=='/lol-lobby/v2/lobby' else original(p)
        self.transport.bodies[Query('ahri',mode='swift').url]=(DATA/'ahri-swift.json').read_bytes()
        self.transport.bodies[Query('jinx',mode='swift').url]=(DATA/'jinx-swift.json').read_bytes()
        self.apply()
        self.assertEqual(len(self.transport.calls),2)
        self.assertIn('/swift/',self.transport.calls[0])
        self.assertEqual(self.lcu.sets['itemSets'][-1]['associatedMaps'],[11])
        self.assertEqual([r['associatedChampions'] for r in self.lcu.sets['itemSets'][1:]],[[103],[222]])
        self.assertEqual(self.lcu.sets['itemSets'][0],self.personal)

    def test_mayhem_real_archetype_items_and_no_arena_or_aram_substitution(self):
        self.lcu.game['gameData'].update(queue={'id':2400},gameMode='KIWI',mapId=12)
        transport=Mock();transport.get.return_value=(DATA/'ahri-mayhem-builds.json').read_bytes()
        self.auto._mayhem_factory=lambda:MayhemClient(transport=transport)
        self.apply();self.assertEqual(self.transport.calls,[])
        self.assertEqual(transport.get.call_count,1)
        self.assertIn('Core sugerido (sem ordem)',str(self.lcu.sets))
        self.assertNotIn('WR',str(self.lcu.sets))

    def test_changed_champion_during_query_and_shutdown_block_late_writes(self):
        entered,release=threading.Event(),threading.Event();original=self.auto._pages
        def slow(*args):entered.set();release.wait(2);return original(*args)
        self.auto._pages=slow
        try:
            self.auto.tick();self.assertTrue(entered.wait(1))
            self.lcu.session['myTeam'][0]['championId']=222
            release.set();self.wait()
            self.assertEqual(self.lcu.sets['itemSets'],[self.personal])
            self.auto.close();read=Mock(side_effect=AssertionError('closed observer read'))
            self.lcu.draft_request=read;self.auto.tick();read.assert_not_called()
        finally:release.set()

    def test_source_failure_is_bounded_and_never_writes_empty_success(self):
        self.auto._pages=Mock(side_effect=TransportError('private error'))
        now=[0];self.auto._clock=lambda:now[0]
        for moment in [0,1,10,11,30,100,200]:
            now[0]=moment;self.auto.tick();self.wait()
        self.assertEqual(self.auto._pages.call_count,3)
        self.assertEqual(self.lcu.sets['itemSets'],[self.personal])
        self.assertNotIn('private error',str(self.auto.diagnostic()))

    def test_disabling_overlay_does_not_disable_item_import_and_arena_never_imports(self):
        runtime=OverlayRuntime(self.lcu,enabled=lambda:False,items_factory=lambda plans:self.auto)
        self.addCleanup(runtime.stop);runtime.poll();self.wait()
        self.assertEqual(self.auto.diagnostic()['code'],'imported')
        calls=len(self.transport.calls)
        self.lcu.game['gameData'].update(queue={'id':1700},gameMode='CHERRY',mapId=30)
        runtime.poll();self.wait();self.assertEqual(len(self.transport.calls),calls)

if __name__=='__main__':unittest.main()
