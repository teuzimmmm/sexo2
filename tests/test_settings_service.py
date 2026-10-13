import tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from sexo2.services.settings import SettingsService
from config import set_config_options,read_config_file
import configparser

class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.autostart=Mock();self.service=SettingsService(validate_path=lambda p:p=='valid',autostart_status=lambda:False,set_autostart=self.autostart,infer_client_path=lambda p:'client')
        self.payload=dict(threshold=.5,monitorAutoResumeTimeout=60,autostart=False,hideEmptyCategories=True,gamePath='valid')
    def test_invalid_path_changes_nothing(self):
        self.payload['gamePath']='invalid'
        with patch('sexo2.services.settings.set_config_options')as write:
            with self.assertRaises(ValueError):self.service.save(self.payload)
        write.assert_not_called();self.autostart.assert_not_called()
    def test_failed_write_restores_windows_autostart(self):
        self.payload['autostart']=True
        with patch('sexo2.services.settings.set_config_options',side_effect=OSError('full')):
            with self.assertRaises(OSError):self.service.save(self.payload)
        self.assertEqual([c.args[0]for c in self.autostart.call_args_list],[True,False])
    def test_nonfinite_values_cannot_be_saved(self):
        for value in [float('nan'),float('inf')]:
            self.payload['threshold']=value
            with self.assertRaises(ValueError):self.service.save(self.payload)
    def test_batch_preserves_other_sections(self):
        with tempfile.TemporaryDirectory()as temp:
            path=Path(temp)/'config.ini';path.write_text('[Other]\nvalue = keep\n',encoding='utf-8')
            with patch('config.get_config_file_path',return_value=path):set_config_options({'General':{'a':'1','b':'2'}},strict=True,atomic_only=True)
            parser=configparser.ConfigParser();read_config_file(parser,path)
            self.assertEqual(parser['Other']['value'],'keep');self.assertEqual(parser['General']['b'],'2')

if __name__=='__main__':unittest.main()
