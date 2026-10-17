from pathlib import Path
import hashlib,json,tempfile,unittest
from sexo2.services.plugin_sync import sync_project_plugins,PluginSyncError,NAMES

class PluginSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name);self.src=root/'source';self.dst=root/'external';self.back=root/'backups';self.manifest=root/'manifest.json'
        known={}
        for name in NAMES:
            for folder,body in [(self.src,b'// new project script'),(self.dst,b'// old project script')]:
                path=folder/name/'index.js';path.parent.mkdir(parents=True);path.write_bytes(body)
            known[name]=[hashlib.sha256(b).hexdigest() for b in [b'// new project script',b'// old project script']]
        self.manifest.write_text(json.dumps({'schema':1,'plugins':known}))
        self.sync=lambda:sync_project_plugins(self.src,self.dst,self.manifest,self.back)

    def test_upgrade_only_known_entrypoints_preserves_every_other_file_and_is_idempotent(self):
        (self.dst/'datastore').write_bytes(b'SYNTHETIC PRIVATE PREF')
        (self.dst/'custom-plugin').mkdir();(self.dst/'custom-plugin/index.js').write_bytes(b'// personal')
        result=self.sync();self.assertTrue(result.changed)
        self.assertEqual((self.dst/'datastore').read_bytes(),b'SYNTHETIC PRIVATE PREF')
        self.assertEqual((self.dst/'custom-plugin/index.js').read_bytes(),b'// personal')
        self.assertEqual(len(list(self.back.rglob('*.js'))),len(NAMES))
        self.assertFalse(self.sync().changed)

    def test_one_customized_script_prevents_all_updates(self):
        (self.dst/NAMES[-1]/'index.js').write_bytes(b'// personal edit')
        with self.assertRaises(PluginSyncError) as ctx:self.sync()
        self.assertEqual(ctx.exception.code,'customized')
        self.assertEqual((self.dst/NAMES[0]/'index.js').read_bytes(),b'// old project script')
        self.assertFalse(self.back.exists())

    def test_disabled_plugins_remain_disabled_and_missing_owned_plugins_can_be_added(self):
        (self.dst/NAMES[0]/'index.js').rename(self.dst/NAMES[0]/'index.js_')
        (self.dst/NAMES[1]/'index.js').unlink()
        result=self.sync();self.assertIn(NAMES[0],result.disabled)
        self.assertFalse((self.dst/NAMES[0]/'index.js').exists())
        self.assertEqual((self.dst/NAMES[1]/'index.js').read_bytes(),b'// new project script')

    def test_malformed_manifest_cannot_write_plugins(self):
        for value in [[], {'schema':1,'plugins':list(NAMES)}, {'schema':2,'plugins':{}}]:
            self.manifest.write_text(json.dumps(value))
            with self.assertRaises(PluginSyncError):self.sync()
            self.assertEqual((self.dst/NAMES[0]/'index.js').read_bytes(),b'// old project script')

    def test_link_target_is_refused(self):
        target=self.dst/NAMES[0]/'index.js';target.unlink()
        try:target.symlink_to(self.src/NAMES[0]/'index.js')
        except OSError:self.skipTest('Symlink privileges unavailable')
        with self.assertRaises(PluginSyncError):self.sync()

    def test_write_failure_rolls_back_unchanged_project_files(self):
        from contextlib import contextmanager
        from unittest.mock import patch
        from utils.core.atomic_file import atomic_write
        @contextmanager
        def fail_second(path,*args,**kwargs):
            if Path(path)==self.dst/NAMES[1]/'index.js':raise OSError('synthetic write failure')
            with atomic_write(path,*args,**kwargs) as file:yield file
        with patch('sexo2.services.plugin_sync.atomic_write',fail_second),self.assertRaises(PluginSyncError):self.sync()
        for name in NAMES:self.assertEqual((self.dst/name/'index.js').read_bytes(),b'// old project script')

    def test_packaged_manifest_recognizes_current_project_sources(self):
        root=Path(__file__).resolve().parents[1]
        data=json.loads((root/'assets/sexo2-managed-plugins.json').read_text())
        for name in NAMES:
            body=(root/'Pengu Loader/plugins'/name/'index.js').read_bytes()
            self.assertIn(hashlib.sha256(body).hexdigest(),data['plugins'][name])

if __name__=='__main__':unittest.main()
