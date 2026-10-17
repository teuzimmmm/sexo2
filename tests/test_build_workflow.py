"""Offline vertical tests: synthetic draft/LCU with real sanitized source data."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from lolalytics import Client, Query
from sexo2.services.builds import BuildService
from sexo2.services.draft import BuildError, DraftReader
from sexo2.services.loadouts import GameCatalog, LoadoutImporter, rune_payload
from tests.test_lolalytics_recommendations import (
    _snapshot, KEYSTONE, KEYSTONE_MANIFEST, MATCHUPS, MATCHUP_MANIFEST,
)

DATA = Path(__file__).parent / 'fixtures' / 'loadouts'


class FakeLCU:
    """All account identifiers and sessions in this fake are synthetic."""
    def __init__(self):
        self.phase = 'ChampSelect'
        self.session = {'localPlayerCellId': 0, 'gameId': 10,
                        'myTeam': [{'cellId': 0, 'championId': 103, 'assignedPosition': 'middle'}],
                        'theirTeam': [{'championId': 1, 'assignedPosition': 'middle'},
                                      {'championId': 13, 'assignedPosition': 'top'}],
                        'timer': {'phase': 'BAN_PICK'}}
        self.game = {'gameData': {'gameId': 10, 'gameMode': 'CLASSIC', 'mapId': 11, 'queue': {'id': 420}}}
        self.champions = [{'id': cid, 'name': name, 'alias': name} for cid, name in [(103,'Ahri'),(1,'Annie'),(13,'Ryze'),(222,'Jinx')]]
        self.account = {'summonerId': 100, 'accountId': 200}
        self.pages = [{'id': 1, 'name': 'Minha página pessoal', 'isEditable': True,
                       'current': True, 'selectedPerkIds': [1], 'primaryStyleId': 8000}]
        self.sets = {'accountId': 200, 'timestamp': 1,
                     'itemSets': [{'uid': 'personal', 'title': 'Meu conjunto', 'blocks': []}]}
        self.requests = []
        self.before_write = None
        self.reject_write = False
        self.drop_write = False

    def get(self, path, timeout=1, **kwargs):
        return deepcopy({'/lol-gameflow/v1/gameflow-phase': self.phase,
                         '/lol-champ-select/v1/session': self.session,
                         '/lol-gameflow/v1/session': self.game,
                         '/lol-game-data/assets/v1/champion-summary.json': self.champions}.get(path))

    def draft_request(self, path):
        return self.get(path)

    def loadout_request(self, method, path, payload=None):
        self.requests.append((method, path, deepcopy(payload)))
        if method == 'GET':
            if path.endswith('/current-summoner'):return deepcopy(self.account)
            if path == '/lol-perks/v1/pages':return deepcopy(self.pages)
            if path.endswith('/sets'):return deepcopy(self.sets)
            if path.endswith('/perkstyles.json'):return json.loads((DATA/'perkstyles.json').read_text())
            if path.endswith('/items.json'):return json.loads((DATA/'items.json').read_text())
            if path.endswith('/perks.json'):return json.loads((DATA/'perks.json').read_text())
            if path.endswith('/cherry-augments.json'):return json.loads((DATA/'cherry-augments.json').read_text())
        else:
            if self.before_write:self.before_write()
            if self.reject_write:raise ValueError('fake capacity failure')
            if self.drop_write:return None
            if path=='/lol-perks/v1/currentpage':
                for page in self.pages:page['current']=page.get('id')==payload
            elif path.startswith('/lol-perks/v1/pages'):
                for page in self.pages:page['current'] = False
                if method == 'POST':
                    self.pages.append(dict(deepcopy(payload), id=max(p['id'] for p in self.pages)+1, isEditable=True))
                else:
                    existing=next(p for p in self.pages if p['id']==int(path.rsplit('/',1)[-1]))
                    existing.update(deepcopy(payload))
            elif path.endswith('/sets'):self.sets=deepcopy(payload)
        return None


class FixtureTransport:
    def __init__(self):
        self.calls=[];self.bodies={}
        for root,manifest in [(KEYSTONE,KEYSTONE_MANIFEST),(MATCHUPS,MATCHUP_MANIFEST)]:
            for row in manifest:
                query=Query(**row['filters'])
                self.bodies[query.url]=(root/row['fixture']).read_bytes()
                params=query.to_dict();params['patch']=None
                self.bodies[Query(**params).url]=(root/row['fixture']).read_bytes()
        from tests.test_lolalytics_recommendations import FIXTURES,MANIFEST
        row=next(r for r in MANIFEST if r['fixture']=='jinx-arena.json')
        for patch_value in [None,'16.20']:
            params=dict(row['filters'],patch=patch_value)
            self.bodies[Query(**params).url]=(FIXTURES/row['fixture']).read_bytes()

    def get(self,url):
        self.calls.append(url)
        if url not in self.bodies:raise AssertionError('Unexpected source request: '+url)
        return self.bodies[url]

    def close(self):pass


def service(lcu=None):
    lcu=lcu or FakeLCU();transport=FixtureTransport()
    return BuildService(lcu,Client(transport=transport),risk=lambda:'medium'),lcu,transport


def query(s, **options):
    context=s.context()
    return s.query(dict(revision=context['revision'],**options),s.begin_query())


class DraftTests(unittest.TestCase):
    def test_normal_draft_and_ranked_use_the_same_sr_source(self):
        for queue_id in (400,430,420,440):
            with self.subTest(queue_id=queue_id):
                lcu=FakeLCU();lcu.game['gameData']['queue']['id']=queue_id
                draft=DraftReader(lcu).read()
                self.assertEqual(draft.mode,'ranked')
                self.assertEqual(bool(draft.warning),queue_id in (400,430))

    def test_projection_ignores_countdown_and_personal_fields(self):
        lcu=FakeLCU();reader=DraftReader(lcu);first=reader.read()
        lcu.session['timer']['adjustedTimeLeftInPhase']=123
        lcu.session['myTeam'][0].update(puuid='SYNTHETIC-PRIVATE',summonerId=99)
        self.assertEqual(first.revision,reader.read().revision)
        self.assertNotIn('SYNTHETIC-PRIVATE',json.dumps(first.to_dict()))
        lcu.session['myTeam'][0]['championId']=222
        self.assertNotEqual(first.revision,reader.read().revision)

    def test_finalization_and_mode_are_explicit(self):
        lcu=FakeLCU();reader=DraftReader(lcu)
        self.assertEqual(reader.read().mode,'ranked')
        lcu.game['gameData']['queue']['id']=450
        self.assertEqual(reader.read().mode,'aram')
        lcu.game['gameData'].update(gameMode='ARAM',mapId=12,queue={'id':9999})
        self.assertIsNone(reader.read().mode)
        lcu.game['gameData']['queue']['id']=1700
        self.assertEqual(reader.read().mode,'arena')
        lcu.session['timer']['phase']='FINALIZATION'
        self.assertTrue(reader.read().finalization)

    def test_no_game_data_requests_outside_champ_select_and_reentry_changes_revision(self):
        lcu=FakeLCU();reader=DraftReader(lcu);first=reader.read().revision
        lcu.phase='Lobby';lobby=reader.read()
        self.assertEqual(lobby.champion_id,0)
        lcu.phase='ChampSelect';self.assertNotEqual(first,reader.read().revision)
        lcu.phase=None
        with self.assertRaises(BuildError):reader.read()

    def test_missing_draft_identity_blocks_ambiguous_session(self):
        lcu=FakeLCU();lcu.session.pop('gameId');lcu.game['gameData'].pop('gameId')
        context=DraftReader(lcu).read()
        self.assertIsNone(context.game_key)
        self.assertEqual(context.mode,'ranked')
        s,_,transport=service(lcu);self.addCleanup(s.close)
        self.assertFalse(s.context()['available'])
        with self.assertRaises(BuildError):query(s)
        self.assertEqual(transport.calls,[])

    def test_missing_player_and_malformed_timer_fail_understandably(self):
        lcu=FakeLCU();lcu.session['localPlayerCellId']=None
        with self.assertRaises(BuildError):DraftReader(lcu).read()
        lcu.session['localPlayerCellId']=0;lcu.session['timer']='bad'
        with self.assertRaises(BuildError):DraftReader(lcu).read()


class BuildServiceTests(unittest.TestCase):
    def test_real_fixture_general_pair_and_warm_cache(self):
        s,lcu,transport=service();self.addCleanup(s.close)
        result=query(s)
        self.assertEqual([p['id'] for p in result['entries']],['wr','common'])
        self.assertEqual(len(transport.calls),3)
        self.assertEqual(result['entries'][0]['page']['keystone'],8992)
        query(s);self.assertEqual(len(transport.calls),3)

    def test_matchup_waits_for_finalization_and_rejects_foreign_target(self):
        s,lcu,transport=service();self.addCleanup(s.close)
        with self.assertRaises(BuildError):query(s,selection='matchup',opponentId=1)
        self.assertEqual(transport.calls,[])
        lcu.session['timer']['phase']='FINALIZATION'
        result=query(s,selection='matchup',opponentId=1)
        self.assertEqual(result['entries'][0]['id'],'vs:1')
        self.assertNotIn('keystone=',transport.calls[0])
        with self.assertRaises(BuildError):query(s,selection='matchup',opponentId=222)

    def test_arena_has_no_champion_select_builds_or_source_requests(self):
        s,lcu,transport=service();self.addCleanup(s.close)
        lcu.session['myTeam'][0]['championId']=222
        lcu.game['gameData'].update(queue={'id':1700},gameMode='CHERRY',mapId=30)
        self.assertEqual(s.context()['mode'],'arena')
        self.assertFalse(s.context()['available'])
        with self.assertRaises(BuildError):query(s)
        self.assertFalse(transport.calls)

    def test_normal_draft_can_prepare_runes_and_related_items(self):
        for queue_id in (400,430):
            with self.subTest(queue_id=queue_id):
                s,lcu,transport=service();self.addCleanup(s.close)
                lcu.game['gameData']['queue']['id']=queue_id
                self.assertTrue(s.context()['available'])
                result=query(s)
                self.assertEqual({r['id']for r in result['entries']},{'wr','common'})
                self.assertTrue(all(r['page']['blocks']for r in result['entries']))

    def test_changing_champion_during_query_discards_result(self):
        s,lcu,transport=service();self.addCleanup(s.close)
        original=s.collector.recommend
        def change(*args,**kwargs):
            response=original(*args,**kwargs)
            lcu.session['myTeam'][0]['championId']=222
            return response
        with patch.object(s.collector,'recommend',side_effect=change):
            with self.assertRaises(BuildError):query(s)
        self.assertFalse(s._pages);self.assertIsNone(s._result_id)

    def test_new_intent_invalidates_queued_query_before_network(self):
        s,lcu,transport=service();self.addCleanup(s.close)
        ctx=s.context();old=s.begin_query();s.begin_query()
        with self.assertRaises(BuildError):s.query({'revision':ctx['revision']},old)
        self.assertFalse(transport.calls)

    def test_prepared_matchup_and_general_pages_remain_distinct(self):
        s,lcu,transport=service();self.addCleanup(s.close)
        lcu.session['timer']['phase']='FINALIZATION'
        query(s);result=query(s,selection='matchup',opponentId=1)
        self.assertEqual({e['id'] for e in result['entries']},{'wr','common','vs:1'})
        self.assertEqual(next(e for e in result['entries'] if e['id']=='vs:1')['page']['conditioning'],'opponent')

    def test_stale_result_and_changed_risk_cannot_import(self):
        s,lcu,transport=service();self.addCleanup(s.close)
        result=query(s);importer=Mock()
        payload=dict(revision=result['revision'],resultId=result['resultId'],entryId='wr',target='runes')
        s.risk=lambda:'high'
        with self.assertRaises(BuildError):s.import_selection(payload,importer)
        importer.apply.assert_not_called()

    def test_integration_import_uses_server_page_not_client_payload(self):
        s,lcu,transport=service();self.addCleanup(s.close)
        result=query(s)
        with tempfile.TemporaryDirectory()as temp:
            importer=LoadoutImporter(lcu,Path(temp)/'owner.json')
            answer=s.import_selection(dict(revision=result['revision'],resultId=result['resultId'],
                entryId='wr',target='runes',runes={'malicious':True}),importer)
        self.assertTrue(answer['verified'])
        self.assertEqual(len(lcu.pages[-1]['selectedPerkIds']),9)


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.lcu=FakeLCU();self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.importer=LoadoutImporter(self.lcu,Path(self.temp.name)/'owner.json')
        snap=_snapshot(KEYSTONE,KEYSTONE_MANIFEST,'ahri-ranked-win.json')
        from lolalytics.builds import build_page
        self.page=build_page(snap,'win',8992)
        self.guard=Mock()

    def apply(self,target):
        return self.importer.apply(target,self.page,[self.page],103,guard=self.guard)

    def test_reuses_owned_rune_page_without_deleting_personal_page(self):
        personal=deepcopy(self.lcu.pages[0]);self.apply('runes');self.apply('runes')
        self.assertEqual(len(self.lcu.pages),2)
        self.assertEqual(self.lcu.pages[0]['name'],personal['name'])
        self.assertEqual(self.lcu.pages[0]['selectedPerkIds'],personal['selectedPerkIds'])
        writes=[m for m,p,b in self.lcu.requests if m!='GET']
        self.assertEqual(writes,['POST','PUT'])
        self.assertEqual(self.lcu.pages[-1]['primaryStyleId'],8200)
        self.assertEqual(self.lcu.pages[-1]['subStyleId'],8400)

    def test_matching_personal_name_is_not_proof_of_ownership(self):
        self.lcu.pages[0]['name']='SEXO2 · WR'
        previous=deepcopy(self.lcu.pages[0]);self.apply('runes')
        self.assertEqual(len(self.lcu.pages),2)
        self.assertEqual(self.lcu.pages[0]['selectedPerkIds'],previous['selectedPerkIds'])
        self.assertEqual(self.lcu.pages[-1]['name'],'SEXO2 · WR')

    def test_same_page_id_in_another_account_does_not_grant_ownership(self):
        self.apply('runes')
        personal=dict(deepcopy(self.lcu.pages[-1]),selectedPerkIds=[999])
        self.lcu.pages=[personal];self.lcu.account={'summonerId':101,'accountId':201}
        self.apply('runes')
        self.assertEqual(self.lcu.pages[0]['selectedPerkIds'],[999])
        self.assertEqual(len(self.lcu.pages),2)

    def test_capacity_failure_never_deletes_a_personal_page(self):
        previous=deepcopy(self.lcu.pages);self.lcu.reject_write=True
        with self.assertRaises(BuildError):self.apply('runes')
        self.assertEqual(self.lcu.pages,previous)
        self.assertFalse(any(m=='DELETE'for m,p,b in self.lcu.requests))

    def test_readback_failure_is_not_success(self):
        self.lcu.drop_write=True
        with self.assertRaisesRegex(BuildError,'confirmada'):self.apply('runes')
        with self.assertRaisesRegex(BuildError,'confirmada'):self.apply('items')

    def test_invalid_rune_or_item_ids_fail_before_writing(self):
        self.page.runes['pri'][0]='999999'
        with self.assertRaises(BuildError):self.apply('runes')
        self.assertFalse(any(m!='GET'for m,p,b in self.lcu.requests))
        self.page.blocks[0].choices[0].identifier='999999'
        with self.assertRaises(BuildError):self.apply('items')
        self.assertFalse(any(m!='GET'for m,p,b in self.lcu.requests))

    def test_items_preserve_personal_sets_and_reuse_managed_slots(self):
        personal=deepcopy(self.lcu.sets['itemSets'][0])
        answer=self.apply('items');self.assertTrue(answer['verified'])
        first=deepcopy(self.lcu.sets['itemSets'][1])
        self.apply('items')
        self.assertEqual(len(self.lcu.sets['itemSets']),2)
        self.assertEqual(self.lcu.sets['itemSets'][0],personal)
        self.assertEqual(first['uid'],self.lcu.sets['itemSets'][1]['uid'])
        self.assertEqual(first['associatedChampions'],[103])
        self.assertIn(str(self.page.blocks[1].metrics['games']),first['blocks'][1]['type'])
        self.assertNotIn(str(self.page.core_metrics['win_rate'])+'%',first['blocks'][-1]['type'])
        self.assertEqual(first['blocks'][1]['items'][0]['id'],self.page.blocks[1].choices[0].identifier)

    def test_item_ownership_is_scoped_to_the_connected_account(self):
        self.apply('items');previous=deepcopy(self.lcu.sets['itemSets'][-1])
        self.lcu.account={'summonerId':101,'accountId':201};self.lcu.sets['accountId']=201
        self.apply('items')
        self.assertEqual(self.lcu.sets['itemSets'][1],previous)
        self.assertNotEqual(self.lcu.sets['itemSets'][-1]['uid'],previous['uid'])

    def test_changed_draft_and_account_block_write(self):
        self.guard.side_effect=BuildError('A seleção mudou')
        with self.assertRaises(BuildError):self.apply('runes')
        self.assertFalse(self.lcu.requests)
        self.guard.side_effect=None
        original=self.importer._account;count=0
        def account():
            nonlocal count
            count+=1
            return original() if count==1 else (999,999)
        with patch.object(self.importer,'_account',side_effect=account):
            with self.assertRaisesRegex(BuildError,'conta'):self.apply('runes')
        self.assertFalse(any(m!='GET'for m,p,b in self.lcu.requests))

    def test_corrupt_owner_registry_does_not_overwrite_pages(self):
        self.importer.path.write_text('{broken')
        with self.assertRaises(BuildError):self.apply('runes')
        self.assertFalse(any(m!='GET'for m,p,b in self.lcu.requests))

    def test_catalog_refreshes_for_new_draft_and_rejects_unknown_schema(self):
        catalog=GameCatalog(self.lcu);catalog.bind_revision('one');catalog.rows('items')
        count=len(self.lcu.requests);catalog.rows('items');self.assertEqual(len(self.lcu.requests),count)
        catalog.bind_revision('two');catalog.rows('items');self.assertEqual(len(self.lcu.requests),count+1)
        with patch.object(self.lcu,'loadout_request',return_value={'schemaVersion':99,'styles':[]}):
            with self.assertRaises(BuildError):catalog.rows('perkstyles')

    def test_augment_names_use_confirmed_cherry_catalog(self):
        self.assertEqual(self.importer.catalog.names('cherry-augments')['1328'],'Critical Rhythm')

    def test_real_style_fixture_and_invalid_secondary_rows(self):
        styles=json.loads((DATA/'perkstyles.json').read_text())['styles']
        body=rune_payload(self.page,styles,'test')
        self.assertEqual(len(body['selectedPerkIds']),9)
        self.page.runes['sec']=['8473','8444']
        with self.assertRaises(BuildError):rune_payload(self.page,styles,'test')


if __name__=='__main__':unittest.main()
