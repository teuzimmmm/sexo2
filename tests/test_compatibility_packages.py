import json,tempfile,unittest,zipfile
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat,PrivateFormat,NoEncryption
from scripts.build_compatibility import generate
from sexo2.update.engine import apply_patch
from updater_main import local_package
from unittest.mock import patch

class CompatibilityPackagesTests(unittest.TestCase):
    def test_each_old_base_gets_direct_update_and_preserves_personal_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);new=root/'new';new.mkdir()
            (new/'SEXO2.exe').write_bytes(b'new');(new/'SEXO2 Update.exe').write_bytes(b'helper')
            registry=root/'bases.json';bases={}
            for label in ['r1','1.5.1']:
                base=root/label;base.mkdir();(base/'SEXO2.exe').write_bytes(label.encode())
                (base/'config.ini').write_bytes(b'personal');bases[label]=str(base)
            registry.write_text(json.dumps(bases));out=root/'release'
            key=Ed25519PrivateKey.generate();public=key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
            entries=generate(registry,new,out,'1.5.2',key.private_bytes(Encoding.Raw,PrivateFormat.Raw,NoEncryption()))
            self.assertEqual(len(entries),2)
            for entry in entries:
                base=Path(bases[entry['base']])
                with patch('updater_main.PUBLIC_KEY',public):
                    chosen=local_package(base,out)
                self.assertEqual(Path(chosen).name,entry['asset'])
                self.assertEqual(apply_patch(chosen,base,public),'1.5.2')
                self.assertEqual((base/'config.ini').read_bytes(),b'personal')
                self.assertEqual((base/'SEXO2.exe').read_bytes(),b'new')
            self.assertEqual(json.loads(registry.read_text())['1.5.2'],str(new))
            with zipfile.ZipFile(out/'SEXO2-Atualizacao-1.5.2.zip') as archive:
                self.assertIn('SEXO2 Update.exe',archive.namelist())
                self.assertEqual(len([n for n in archive.namelist() if n.endswith('.zip')]),2)

    def test_missing_supported_base_fails_before_creating_packages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);registry=root/'bases.json';registry.write_text(json.dumps({'r1':str(root/'missing')}))
            with self.assertRaisesRegex(ValueError,'Missing supported baseline'):
                generate(registry,root/'new',root/'out','1.5.2',b'x'*32)
            self.assertFalse((root/'out').exists())
