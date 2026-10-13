import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from updater_main import plan_update,local_package

class TransitionTests(unittest.TestCase):
    def test_old_version_without_matching_package_gives_instructions_before_network(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);(root/'SEXO2.exe').write_bytes(b'old version')
            with self.assertRaisesRegex(ValueError,'pacote de transição'):
                plan_update(root,folder=root)
    def test_missing_app_does_not_try_to_read_update_source(self):
        with tempfile.TemporaryDirectory()as temp:
            with self.assertRaisesRegex(ValueError,'SEXO2.exe'):plan_update(temp,folder=temp)
    def test_existing_local_package_is_used_by_old_installation(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);(root/'SEXO2.exe').write_bytes(b'old');package=root/'patch.zip';package.write_bytes(b'fixture')
            self.assertEqual(plan_update(root,str(package)),(root,str(package)))

if __name__=='__main__':unittest.main()
