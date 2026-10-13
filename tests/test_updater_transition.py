import tempfile,unittest
from pathlib import Path
from unittest.mock import patch, Mock
from updater_main import plan_update,local_package,ensure_closed

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

class UpdateProcessTests(unittest.TestCase):
    def process(self,name):
        process=Mock();process.info={'name':name};return process

    def test_league_client_and_match_do_not_block_update(self):
        processes=[self.process(name) for name in ['LeagueClient.exe','LeagueClientUx.exe','League of Legends.exe','League of Legends (TM) Client.exe']]
        with patch('updater_main.psutil.process_iter',return_value=processes):
            ensure_closed()
        for process in processes:
            process.kill.assert_not_called();process.terminate.assert_not_called()

    def test_running_sexo2_still_blocks_replacing_its_executable(self):
        with patch('updater_main.psutil.process_iter',return_value=[self.process('SEXO2.EXE')]):
            with self.assertRaisesRegex(ValueError,'Feche apenas o SEXO2'):
                ensure_closed()

    def test_legacy_rose_process_still_blocks_replacement(self):
        with patch('updater_main.psutil.process_iter',return_value=[self.process('Rose.exe')]):
            with self.assertRaises(ValueError):ensure_closed()

if __name__=='__main__':unittest.main()
