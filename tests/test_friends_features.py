import json,tempfile,unittest,zipfile,time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from state import SharedState
from pengu.processing.swiftplay_pins import SwiftplayPins
from injection.mods.zip_resolver import ZipResolver
from friends.preferences import Preferences
from friends.service import FriendsService
from friends.lottery import eligible,draw
from friends.diagnostics import sanitize,export_report

class PreferencesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.path=Path(self.temp.name)/'prefs.json';self.prefs=Preferences(self.path)
    def test_persistence_activate_delete_and_exclusions(self):
        self.prefs.save_profile('Arcane',{'11':{'skinId':11001,'name':'Arcane'}});self.prefs.activate('Arcane');self.prefs.exclusions([11002])
        loaded=Preferences(self.path);self.assertEqual(loaded.snapshot()['active_profile'],'Arcane');self.assertEqual(loaded.snapshot()['excluded'],[11002])
        loaded.delete('Arcane');self.assertIsNone(loaded.snapshot()['active_profile'])
    def test_invalid_skin_does_not_write(self):
        with self.assertRaises(ValueError):self.prefs.save_profile('Bad',{'11':{'skinId':22001}})
        self.assertFalse(self.path.exists())
    def test_failed_save_does_not_change_memory(self):
        with patch('friends.preferences.atomic_write',side_effect=OSError('disk')):
            with self.assertRaises(OSError):self.prefs.save_profile('A',{'11':{'skinId':11001}})
        self.assertEqual(self.prefs.snapshot()['profiles'],{})
    def test_corrupt_file_preserved(self):
        self.path.write_text('broken');prefs=Preferences(self.path)
        with self.assertRaises(ValueError):prefs.save_profile('A',{'11':{'skinId':11001}})
        self.assertEqual(self.path.read_text(),'broken')

class DiagnosticTests(unittest.TestCase):
    def test_sanitizer_removes_secrets_links_users_paths(self):
        raw='room S3XO-ROOM-PRIVATE\nhttps://host.trycloudflare.com/#rose=secret-token\nAuthorization: Basic abc123\nrelay_access = abcSECRET\n[PARTY] Matheus joined\nuserpath C:\\Users\\Matheus\\secret\\config.ini\nknown xyzKEY'
        result=sanitize(raw,['xyzKEY'])
        for secret in ['S3XO-ROOM-PRIVATE','secret-token','abc123','abcSECRET','Matheus','xyzKEY']:self.assertNotIn(secret,result)
    def test_quoted_authorization_and_lockfile_credentials_are_removed(self):
        raw="{'Authorization': 'Basic abc123'}\nLeagueClient:123:40000:secretLCU:https\n"
        result=sanitize(raw)
        self.assertNotIn('abc123',result);self.assertNotIn('secretLCU',result)

    def test_archive_is_sanitized_valid_json_and_no_config(self):
        with tempfile.TemporaryDirectory()as d:
            root=Path(d);logs=root/'logs';logs.mkdir();(logs/'rose_test.log').write_text('Authorization: Basic ABC\nSecret TOKEN_PRIVATE\n',encoding='utf-8')
            snapshot={'version':'1','phase':'Lobby','queueId':480,'readiness':{'checks':[{'detail':'C:\\Users\\Person\\private https://private/#rose=TOKEN_PRIVATE'}]},'members':[{'id':123,'name':'RealPerson','connected':True}]}
            target=export_report(root/'exports',snapshot,logs,['TOKEN_PRIVATE'])
            with zipfile.ZipFile(target)as z:
                data=''.join(z.read(n).decode()for n in z.namelist());json.loads(z.read('resumo.json'))
                for secret in ['TOKEN_PRIVATE','RealPerson','Person','ABC']:self.assertNotIn(secret,data)
                self.assertNotIn('config.ini',z.namelist())

class LotteryTests(unittest.TestCase):
    def test_theme_exclusions_base_and_availability(self):
        skins=[{'skinId':11000,'name':'Base'},{'skinId':11001,'name':'PROJETO: A'},{'skinId':11002,'name':'PROJECT B'},{'skinId':11003,'name':'Arcane'}]
        selected=eligible(skins,'PROJETO',{11002},lambda sid:sid!=11003)
        self.assertEqual([s['skinId']for s in selected],[11001])
    def test_deterministic_and_no_silent_theme_fallback(self):
        picks=[{'skinId':11001},{'skinId':11002}]
        self.assertEqual(draw(picks,'seed',1,11),draw(picks,'seed',1,11))
        with self.assertRaises(ValueError):draw([],'seed',1,11)

class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.phase='ChampSelect';self.ids=[11];self.members=[1,2];self.lcu=Mock(ok=True);self.lcu.get.side_effect=self.get;self.lcu.set_my_selection_skin.return_value=True
        self.state=SharedState();self.state.locked_champ_id=11;self.state.own_champion_locked=True;self.state.current_queue_id=420;self.state.champ_select_generation=1;self.state.owned_skin_ids=set();self.state.last_hovered_skin_id=11001
        self.state.swiftplay_pins=SwiftplayPins(self.root/'pins.json')
        tools=self.root/'tools';tools.mkdir();(tools/'mod-tools.exe').touch();(tools/'cslol-dll.dll').touch()
        skins=self.root/'skins';skins.mkdir()
        for cid in [11,22]:
            for n in [1,2]:
                path=skins/str(cid)/str(cid*1000+n)/f'{cid*1000+n}.zip';path.parent.mkdir(parents=True,exist_ok=True)
                with zipfile.ZipFile(path,'w')as z:z.writestr('WAD/test.wad.client','test')
        manager=SimpleNamespace(tools_dir=tools,game_dir=self.root/'game',_injection_in_progress=False,injector=SimpleNamespace(tools_dir=tools,zip_resolver=ZipResolver(skins)))
        self.service=FriendsService(self.state,self.lcu,manager,self.root)
        self.relays=SimpleNamespace(connected=True,members=[{'summoner_id':1,'summoner_name':'A'},{'summoner_id':2,'summoner_name':'B'}])
        self.party=SimpleNamespace(enabled=True,_relays={'room':self.relays},party_state=SimpleNamespace(my_summoner_id=1),_lobby_matcher=SimpleNamespace(get_all_summoner_ids=lambda:set(self.members)),get_state_dict=lambda:{'relay_connected':True})
        self.state.party_manager=self.party
        for target,value in [('friends.service.check_ltk_patcher',SimpleNamespace(missing=[],expired_for=lambda game:False)),('friends.service.read_game_build',100),('friends.service.load_historic_map',{})]:
            p=patch(target,return_value=value);p.start();self.addCleanup(p.stop)
    def get(self,path):
        if path=='/lol-gameflow/v1/gameflow-phase':return self.phase
        if path=='/lol-lobby/v2/lobby':
            if self.phase=='Lobby':return {'gameConfig':{'queueId':480},'localMember':{'playerSlots':[{'championId':cid,'skinId':cid*1000}for cid in self.ids]},'members':[{'summonerId':sid}for sid in self.members]}
            return None
        if path=='/lol-champ-select/v1/session':return {'localPlayerCellId':0,'myTeam':[{'cellId':0,'championId':self.ids[0],'summonerId':1},{'cellId':1,'championId':22,'summonerId':2}]}
        if path=='/lol-summoner/v1/current-summoner':return {'summonerId':1}
        if path.startswith('/lol-game-data/'):
            cid=int(path.split('/')[-1].split('.')[0]);return {'name':f'Champion {cid}','skins':[{'id':cid*1000+n,'name':['Base','Arcane','PROJETO','Unavailable'][n]}for n in range(4)]}
    def test_readiness_detects_missing_archive_and_tools(self):
        self.assertTrue(self.service.readiness()['localReady'])
        self.state.last_hovered_skin_id=11003
        self.assertFalse(self.service.readiness()['localReady'])
        self.state.last_hovered_skin_id=11001;(self.root/'tools/cslol-dll.dll').unlink()
        self.assertFalse(self.service.readiness()['localReady'])
    def test_peer_file_missing_blocks_preflight(self):
        self.relays.members[1]['skin']={'friends':{'version':1,'choices':[{'champion_id':22,'skin_id':22003}],'ready':True}}
        readiness=self.service.readiness();self.assertFalse(readiness['localReady']);self.assertTrue(any(c['id'].startswith('peer-skin')for c in readiness['checks']))
    def test_profile_apply_sets_native_historic_choice_once(self):
        self.service.preferences.save_profile('Project',{'11':{'skinId':11002,'name':'PROJETO'}})
        result=self.service.handle({'action':'apply-profile','name':'Project'})
        self.assertEqual(self.state.historic_skin_id,11002);self.assertTrue(self.state.historic_mode_active)
        self.lcu.set_my_selection_skin.assert_called_once_with(11000)
        self.assertEqual(result['activeProfile'],'Project')
    def test_profile_survives_first_base_skin_detection(self):
        from ui.handlers.historic_mode_handler import HistoricModeHandler
        self.service.apply({'11':{'skinId':11002}})
        with patch('utils.core.historic.get_historic_skin_for_champion',return_value=11001):
            HistoricModeHandler(self.state).check_and_activate(11000)
        self.assertEqual(self.state.historic_skin_id,11002)
    def test_active_profile_applies_new_confirmed_champion(self):
        self.service.preferences.save_profile('Group',{'11':{'skinId':11001},'22':{'skinId':22002}})
        self.service.handle({'action':'apply-profile','name':'Group'})
        self.ids=[22];self.state.locked_champ_id=22;self.state.champ_select_generation=2
        self.service.snapshot()
        self.assertEqual(self.state.historic_skin_id,22002)
    def test_classic_preflight_uses_classic_library(self):
        self.state.current_game_mode='JADE';cid=60011;sid=60011002
        directory=self.root/'classic';path=directory/str(cid)/'11002'/'11002.zip';path.parent.mkdir(parents=True)
        with zipfile.ZipFile(path,'w')as z:z.writestr('WAD/test','data')
        self.service.manager.injector.classic_dir=directory
        self.service.manager.injector.classic_resolver=ZipResolver(directory)
        self.assertTrue(self.service.archive(cid,sid))

    def test_profile_wrong_champion_and_locked_game_are_not_applied(self):
        self.phase='InProgress'
        with self.assertRaises(ValueError):self.service.apply({'11':{'skinId':11002}})
        self.lcu.set_my_selection_skin.assert_not_called()
    def test_profile_saves_catalog_edits_and_survives_restart(self):
        self.service.handle({'action':'save-profile','name':'Favorites','selections':{'11':{'skinId':11002}}})
        loaded=Preferences(self.root/'friends-preferences.json');self.assertEqual(loaded.snapshot()['profiles']['Favorites']['11']['skinId'],11002)
    def test_swiftplay_profile_applies_both_local_slots(self):
        self.phase='Lobby';self.ids=[11,22];self.state.current_queue_id=480
        self.service.apply({'11':{'skinId':11001},'22':{'skinId':22002}})
        self.assertEqual(self.state.swiftplay_skin_tracking,{11:11001,22:22002})
    def test_group_draw_requires_optin(self):
        request={'seed':'a'*32,'created':int(time.time()*1000),'theme':'Arcane','targets':[1,2]}
        self.relays.members[1]['skin']={'friends':{'version':1,'lottery':request,'choices':[]}}
        self.service.snapshot();self.lcu.set_my_selection_skin.assert_not_called()
        self.service.handle({'action':'lottery-optin','enabled':True})
        self.assertEqual(self.state.historic_skin_id,11001);self.assertTrue(self.service.draw_result['success'])
    def test_other_lobby_cannot_draw_our_skins(self):
        self.service.optin=True
        self.relays.members.append({'summoner_id':99,'skin':{'friends':{'version':1,'lottery':{'seed':'b'*32,'created':int(time.time()*1000),'theme':'PROJETO','targets':[1]}}}})
        self.service.snapshot();self.lcu.set_my_selection_skin.assert_not_called()
    def test_exclusion_persists_and_empty_theme_is_explicit(self):
        self.service.handle({'action':'exclude','skinId':11001,'excluded':True})
        result=self.service.handle({'action':'lottery-local','theme':'Arcane'})
        self.assertFalse(result['drawResult']['success']);self.assertIn('Nenhuma skin',result['drawResult']['error'])
        self.lcu.set_my_selection_skin.assert_not_called()
    def test_missing_custom_archive_not_reported_as_ready(self):
        path=self.root/'skins/11/11001/11001.zip';path.write_text('unfinished')
        self.assertFalse(self.service.readiness()['localReady'])
    def test_local_board_does_not_tell_r5_owner_to_update(self):
        members=self.service.snapshot()['members'];self.assertTrue(members[0]['supportsTools']);self.assertTrue(members[0]['local'])

    def test_apply_checks_archive_again_before_client_mutation(self):
        self.assertTrue(self.service.archive(11,11001))
        (self.root/'skins/11/11001/11001.zip').unlink()
        with self.assertRaises(ValueError):self.service.apply({'11':{'skinId':11001}})
        self.lcu.set_my_selection_skin.assert_not_called()
    def test_real_background_bridge_route_returns_panel_state(self):
        import threading
        from pengu.communication.message_handler import MessageHandler
        handler=object.__new__(MessageHandler)
        handler._friends_service=self.service;handler._background_lock=threading.Lock();handler._background_queue=None
        received=[];event=threading.Event()
        def send(text):received.append(json.loads(text));event.set()
        handler._send_response=send
        handler.handle_message(json.dumps({'type':'friends-request','action':'snapshot','requestId':'route-test'}))
        self.assertTrue(event.wait(3))
        self.assertEqual(received[0]['type'],'friends-state');self.assertEqual(received[0]['requestId'],'route-test')
        self.assertIn('readiness',received[0]);self.assertIn('profiles',received[0])

    def test_profile_preserves_chroma_and_draw_uses_base_skins(self):
        original=self.get
        def data(path):
            result=original(path)
            if path.endswith('/11.json'):result['skins'][1]['chromas']=[{'id':11011,'name':'Azul'}]
            return result
        self.lcu.get.side_effect=data
        path=self.root/'skins/11/11001/11011/11011.zip';path.parent.mkdir(parents=True)
        with zipfile.ZipFile(path,'w')as z:z.writestr('WAD/test','data')
        self.state.last_hovered_skin_id=11011
        self.service.handle({'action':'save-profile','name':'Azul'})
        self.service.handle({'action':'apply-profile','name':'Azul'})
        self.assertEqual(self.state.historic_skin_id,11011)
        self.assertEqual(self.service.preferences.snapshot()['profiles']['Azul']['11']['skinId'],11011)
        candidates=eligible(self.service.catalogs.catalog(11)['skins'],'Arcane',set(),lambda sid:True)
        self.assertEqual([p['skinId']for p in candidates],[11001])

    def test_corrupt_preferences_block_draw_and_preserve_choice(self):
        self.service.preferences.error='Arquivo ilegível'
        with self.assertRaises(ValueError):self.service.handle({'action':'lottery-local','theme':'Arcane'})
        self.lcu.set_my_selection_skin.assert_not_called()
        self.assertFalse(self.service.readiness()['localReady'])
    def test_profile_save_failure_cannot_change_client(self):
        self.service.preferences.save_profile('A',{'11':{'skinId':11002}})
        with patch.object(self.service.preferences,'activate',side_effect=OSError('disk')):
            with self.assertRaises(OSError):self.service.handle({'action':'apply-profile','name':'A'})
        self.lcu.set_my_selection_skin.assert_not_called()
    def test_failed_client_confirmation_restores_active_profile(self):
        self.service.preferences.save_profile('A',{'11':{'skinId':11002}})
        self.lcu.set_my_selection_skin.return_value=False
        with self.assertRaises(ValueError):self.service.handle({'action':'apply-profile','name':'A'})
        self.assertIsNone(self.service.preferences.snapshot()['active_profile'])
