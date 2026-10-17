"""Incident regressions: synthetic LCU deliberately serializes native defaults."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock,patch

from tests import test_build_workflow as workflow
from tests.test_build_workflow import FakeLCU
from sexo2.services.draft import BuildError
from sexo2.services.loadouts import LoadoutImporter
from sexo2.services.settings import get_overlay_enabled
from sexo2.overlay.runtime import OverlayRuntime
from lcu.core.request_error import LCURequestError

class IncidentImportTests(unittest.TestCase):
    def setUp(self):workflow.ImportTests.setUp(self)

    def apply(self,target):return self.importer.apply(target,self.page,[self.page],103,guard=self.guard)

    def test_explicit_existing_page_works_when_new_page_capacity_is_full_and_keeps_original_backup(self):
        original=deepcopy(self.lcu.pages[0]);request=self.lcu.loadout_request
        def full(method,path,payload=None):
            if method=='POST' and path=='/lol-perks/v1/pages':raise ValueError('page capacity')
            return request(method,path,payload)
        self.lcu.loadout_request=full
        with self.assertRaises(BuildError):self.apply('runes')
        result=self.importer.apply('runes',self.page,[self.page],103,guard=self.guard,rune_page_id=1)
        self.assertTrue(result['verified']);self.assertEqual(len(self.lcu.pages),1)
        backup=self.importer.path.with_name('sexo2-rune-backups.json')
        original_backup=backup.read_text()
        self.assertEqual(next(iter(json.loads(original_backup).values()))['selectedPerkIds'],original['selectedPerkIds'])
        self.importer.apply('runes',self.page,[self.page],103,guard=self.guard,rune_page_id=1)
        self.assertEqual(backup.read_text(),original_backup)
        self.assertFalse(any(m=='DELETE' for m,p,b in self.lcu.requests))

    def test_native_default_fields_and_reordered_set_list_are_success_but_changed_content_is_failure(self):
        original=self.lcu.loadout_request
        def serialize(method,path,payload=None):
            value=original(method,path,payload)
            if method=='GET' and path.endswith('/sets'):
                for row in value['itemSets']:
                    row.setdefault('startedFrom','')
                    for block in row['blocks']:
                        block.setdefault('showIfSummonerSpell','');block.setdefault('hideIfSummonerSpell','')
                value['itemSets'].reverse()
            return value
        self.lcu.loadout_request=serialize
        self.assertTrue(self.apply('items')['verified'])
        self.assertEqual(self.lcu.sets['itemSets'][0]['uid'],'personal')
        def changed(method,path,payload=None):
            value=serialize(method,path,payload)
            if method=='GET' and path.endswith('/sets') and any(m=='PUT' for m,p,b in self.lcu.requests):
                value['itemSets'][0]['blocks'][0]['items'][0]['count']+=1
            return value
        # Start fresh; mutate only read-back after writing, never the initial read.
        self.lcu.requests=[];self.lcu.loadout_request=changed
        with self.assertRaises(BuildError):self.apply('items')

    def test_saving_page_then_explicitly_selecting_it_is_verified(self):
        request=self.lcu.loadout_request
        def inactive(method,path,payload=None):
            result=request(method,path,payload)
            if method=='POST' and path=='/lol-perks/v1/pages':self.lcu.pages[-1]['current']=False
            return result
        self.lcu.loadout_request=inactive
        self.assertTrue(self.apply('runes')['verified'])
        self.assertTrue(self.lcu.pages[-1]['current'])
        self.assertTrue(any(m=='PUT' and p=='/lol-perks/v1/currentpage' for m,p,b in self.lcu.requests))

    def test_http_reason_reaches_user_without_private_response_or_url(self):
        self.lcu.loadout_request=Mock(side_effect=LCURequestError('http',403))
        with self.assertRaisesRegex(BuildError,'HTTP 403'):self.apply('items')
        self.assertNotIn('127.0.0.1',str(LCURequestError('http',403)))

    def test_foreign_or_protected_page_cannot_be_targeted(self):
        for target in [999,True,-1]:
            with self.assertRaises(BuildError):self.importer.apply('runes',self.page,[self.page],103,guard=self.guard,rune_page_id=target)
        self.lcu.pages[0]['isEditable']=False
        with self.assertRaises(BuildError):self.importer.apply('runes',self.page,[self.page],103,guard=self.guard,rune_page_id=1)
        self.assertFalse(any(m!='GET' for m,p,b in self.lcu.requests))

class IncidentRuntimeTests(unittest.TestCase):
    def test_production_loading_never_creates_legacy_renderer_ocr_or_display_child(self):
        lcu=FakeLCU();lcu.phase='InProgress';items=Mock()
        runtime=OverlayRuntime(lcu,enabled=lambda:True,items_factory=lambda plans:items)
        self.addCleanup(runtime.stop)
        with patch('sexo2.overlay.win32.NativeOverlay',side_effect=AssertionError('legacy renderer')),patch('sexo2.overlay.reader.OfferReader',side_effect=AssertionError('OCR during loading')),patch('sexo2.overlay.readiness.GameReadiness.check',return_value=False),patch('sexo2.overlay.isolated.subprocess.Popen') as spawn:
            runtime.start()
            deadline=time.monotonic()+2
            while not items.tick.called and time.monotonic()<deadline:time.sleep(.01)
            self.assertTrue(items.tick.called)
            self.assertIsNone(runtime._window._child)
            self.assertFalse(runtime.frame().active)
            self.assertEqual(runtime.diagnostic()['code'],'loading')
            spawn.assert_not_called()
        with patch('sexo2.services.settings.get_config_option',return_value='true'):
            self.assertTrue(get_overlay_enabled())

if __name__=='__main__':unittest.main()
