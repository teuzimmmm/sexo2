import unittest
from unittest.mock import Mock,patch
from sexo2.update.client import check_release

class UpdateClientTests(unittest.TestCase):
    def test_private_auth_failure_keeps_project_link_without_exposing_token(self):
        response=Mock(status_code=404)
        with patch('sexo2.update.client.requests.get',return_value=response)as get:
            result=check_release('teuzimmmm/sexo2','synthetic-test-token')
        self.assertFalse(result['available']);self.assertEqual(result['github'],'https://github.com/teuzimmmm/sexo2')
        self.assertNotIn('synthetic-test-token',str(result))
        self.assertEqual(get.call_args.kwargs['headers']['Authorization'],'Bearer synthetic-test-token')
    def test_new_release_offers_only_expected_update_asset(self):
        response=Mock(status_code=200)
        response.json.return_value={'tag_name':'v1.5.1','assets':[{'name':'SEXO2-update.zip','id':10}]}
        with patch('sexo2.update.client.requests.get',return_value=response):result=check_release('teuzimmmm/sexo2','',current='1.5.0')
        self.assertTrue(result['available']);self.assertEqual(result['assetId'],10)
    def test_prerelease_is_not_offered_as_stable_update(self):
        response=Mock(status_code=200)
        response.json.return_value={'tag_name':'v1.5.1','prerelease':True,'assets':[]}
        with patch('sexo2.update.client.requests.get',return_value=response):
            with self.assertRaises(ValueError):check_release('teuzimmmm/sexo2','')

    def test_skipped_versions_choose_direct_compatible_patch(self):
        response=Mock(status_code=200)
        response.json.return_value={'tag_name':'v1.8.0','assets':[{'name':'SEXO2-update.zip','id':1},{'name':'SEXO2-update-from-1.5.1.zip','id':2}]}
        with patch('sexo2.update.client.requests.get',return_value=response):
            result=check_release('teuzimmmm/sexo2','',current='1.5.1')
        self.assertTrue(result['available']);self.assertEqual(result['assetId'],2)

    def test_unknown_base_is_not_offered_wrong_primary_patch(self):
        response=Mock(status_code=200)
        response.json.return_value={'tag_name':'v1.8.0','assets':[{'name':'SEXO2-update.zip','id':1},{'name':'SEXO2-update-from-1.5.1.zip','id':2}]}
        with patch('sexo2.update.client.requests.get',return_value=response):
            result=check_release('teuzimmmm/sexo2','',current='1.4.7')
        self.assertFalse(result['available']);self.assertIsNone(result['assetId'])
        self.assertIn('transição',result['message'])

if __name__=='__main__':unittest.main()
