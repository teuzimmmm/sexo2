import tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from sexo2.services.settings import SettingsService
from config import set_config_options,read_config_file
import configparser

class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.autostart=Mock();self.service=SettingsService(validate_path=lambda p:p=='valid',autostart_status=lambda:False,set_autostart=self.autostart,infer_client_path=lambda p:'client')
        self.payload=dict(threshold=.5,monitorAutoResumeTimeout=60,autostart=False,hideEmptyCategories=True,gamePath='valid',buildOverlayEnabled=False)
    def test_invalid_path_changes_nothing(self):
        self.payload['gamePath']='invalid'
        with patch('sexo2.services.settings.set_config_options')as write:
            with self.assertRaises(ValueError):self.service.save(self.payload)
        write.assert_not_called();self.autostart.assert_not_called()
    def test_overlay_setting_persists_and_old_panels_preserve_it(self):
        with patch('sexo2.services.settings.set_config_options') as write:
            self.payload['buildOverlayEnabled']=False
            self.assertFalse(self.service.save(self.payload)['buildOverlayEnabled'])
            self.assertEqual(write.call_args.args[0]['LoLalytics']['overlay_enabled'],'false')
        self.payload.pop('buildOverlayEnabled')
        with patch('sexo2.services.settings.get_overlay_enabled',return_value=False), patch('sexo2.services.settings.set_config_options') as write:
            self.assertFalse(self.service.save(self.payload)['buildOverlayEnabled'])
            self.assertEqual(write.call_args.args[0]['LoLalytics']['overlay_enabled'],'false')
    def test_invalid_overlay_setting_has_no_side_effects(self):
        self.payload['buildOverlayEnabled']='false'
        with patch('sexo2.services.settings.set_config_options') as write,self.assertRaises(ValueError):
            self.service.save(self.payload)
        write.assert_not_called()
    def test_failed_write_restores_windows_autostart(self):
        self.payload['autostart']=True
        with patch('sexo2.services.settings.set_config_options',side_effect=OSError('full')):
            with self.assertRaises(OSError):self.service.save(self.payload)
        self.assertEqual([c.args[0]for c in self.autostart.call_args_list],[True,False])
    def test_nonfinite_values_cannot_be_saved(self):
        for value in [float('nan'),float('inf')]:
            self.payload['threshold']=value
            with self.assertRaises(ValueError):self.service.save(self.payload)
    def test_snapshot_uses_default_for_corrupt_risk_level(self):
        with patch('sexo2.services.settings.get_config_option', side_effect=lambda section, key, fallback=None: 'bogus' if (section,key)==('LoLalytics','risk_level') else fallback):
            self.assertEqual(self.service.snapshot()['lolalyticsRiskLevel'], 'medium')
    def test_snapshot_reads_saved_risk_level_and_defaults_when_missing(self):
        with patch('sexo2.services.settings.get_config_option', side_effect=lambda section, key, fallback=None: 'very-low' if (section,key)==('LoLalytics','risk_level') else fallback):
            self.assertEqual(self.service.snapshot()['lolalyticsRiskLevel'], 'very-low')
        with patch('sexo2.services.settings.get_config_option', side_effect=lambda section, key, fallback=None: fallback):
            self.assertEqual(self.service.snapshot()['lolalyticsRiskLevel'], 'medium')
    def test_risk_level_persists_with_existing_settings(self):
        with patch('sexo2.services.settings.set_config_options') as write:
            self.payload['lolalyticsRiskLevel']='high'
            result=self.service.save(self.payload)
        self.assertEqual(result['lolalyticsRiskLevel'],'high')
        write.assert_called_once()
        self.assertEqual(write.call_args.args[0]['LoLalytics'], {'risk_level':'high','overlay_enabled':'false'})
        self.assertTrue(write.call_args.kwargs['strict'])
        self.assertTrue(write.call_args.kwargs['atomic_only'])
    def test_risk_level_uses_atomic_config_batch_and_keeps_other_sections(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'config.ini'
            path.write_text('[Other]\nkeep = yes\n',encoding='utf-8')
            self.payload['lolalyticsRiskLevel']='very-low'
            with patch('config.get_config_file_path',return_value=path):
                self.service.save(self.payload)
            parser=configparser.ConfigParser(interpolation=None)
            read_config_file(parser,path)
            self.assertEqual(parser['LoLalytics']['risk_level'],'very-low')
            self.assertEqual(parser['Other']['keep'],'yes')
    def test_old_payload_preserves_saved_risk_level(self):
        with patch('sexo2.services.settings.get_config_option', side_effect=lambda section, key, fallback=None: 'low' if (section,key)==('LoLalytics','risk_level') else fallback), patch('sexo2.services.settings.set_config_options') as write:
            result=self.service.save(self.payload)
        self.assertEqual(result['lolalyticsRiskLevel'],'low')
        self.assertEqual(write.call_args.args[0]['LoLalytics']['overlay_enabled'],'false')
    def test_invalid_risk_level_has_no_side_effects(self):
        for invalid in (None, True, 1, [], 'unsupported'):
            with self.subTest(value=invalid):
                self.payload['lolalyticsRiskLevel']=invalid
                with patch('sexo2.services.settings.set_config_options') as write, self.assertRaises(ValueError):
                    self.service.save(self.payload)
                write.assert_not_called();self.autostart.assert_not_called()
    def test_batch_preserves_other_sections(self):
        with tempfile.TemporaryDirectory()as temp:
            path=Path(temp)/'config.ini';path.write_text('[Other]\nvalue = keep\n',encoding='utf-8')
            with patch('config.get_config_file_path',return_value=path):set_config_options({'General':{'a':'1','b':'2'}},strict=True,atomic_only=True)
            parser=configparser.ConfigParser();read_config_file(parser,path)
            self.assertEqual(parser['Other']['value'],'keep');self.assertEqual(parser['General']['b'],'2')

if __name__=='__main__':unittest.main()
