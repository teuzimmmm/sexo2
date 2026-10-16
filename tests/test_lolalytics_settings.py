import unittest
from unittest.mock import Mock, patch

from sexo2.services.lolalytics import LolalyticsService


class LolalyticsSettingsTests(unittest.TestCase):
    def test_saved_level_is_passed_to_client(self):
        client = Mock(recommend=Mock(return_value={'ok': True}))
        service = LolalyticsService(client)
        with patch('sexo2.services.settings.get_config_option', return_value='high'):
            result = service.recommend({'champion': 'ahri'})
        self.assertEqual(result, {'ok': True})
        client.recommend.assert_called_once_with({'champion': 'ahri'}, risk_level='high')

    def test_explicit_valid_level_overrides_saved_setting(self):
        client = Mock(recommend=Mock(return_value='result'))
        service = LolalyticsService(client)
        with patch('sexo2.services.settings.get_config_option', return_value='low'):
            result = service.recommend('query', risk_level='very-high')
        self.assertEqual(result, 'result')
        client.recommend.assert_called_once_with('query', risk_level='very-high')

    def test_invalid_explicit_level_is_rejected_before_client_call(self):
        client = Mock()
        service = LolalyticsService(client)
        with self.assertRaises(ValueError):
            service.recommend('query', risk_level='invalid')
        client.recommend.assert_not_called()


if __name__ == '__main__':
    unittest.main()
