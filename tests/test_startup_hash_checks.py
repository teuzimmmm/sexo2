import threading
import unittest
from unittest.mock import patch
import requests
from utils.download import hash_updater as updater

class StartupHashTests(unittest.TestCase):
    def state(self):
        return {'files': {name: {'sha':'same'} for name in updater.HASH_FILES}}

    def test_checks_overlap_with_separate_sessions_and_keep_state(self):
        barrier=threading.Barrier(3)
        sessions=[]
        lock=threading.Lock()
        def check(path, session):
            with lock: sessions.append(session)
            barrier.wait(timeout=3)
            return {'sha':'same'}
        with patch.object(updater,'load_state',return_value=self.state()), patch.object(updater,'check_file_commits',side_effect=check):
            self.assertFalse(updater.check_for_updates())
        self.assertEqual(len(sessions),9)
        self.assertEqual(len({id(s) for s in sessions}),9)

    def test_changed_file_requests_update(self):
        with patch.object(updater,'load_state',return_value=self.state()), patch.object(updater,'check_file_commits',return_value={'sha':'new'}):
            self.assertTrue(updater.check_for_updates())

    def test_rate_limit_is_recognized_even_with_false_response(self):
        response=requests.Response(); response.status_code=429
        session=unittest.mock.Mock()
        session.get.return_value=response
        with self.assertLogs(level='WARNING'):
            self.assertEqual(updater.check_file_commits('hashes/lol/example',session),{'rate_limited':True})

    def test_rate_limit_does_not_trigger_download_for_existing_state(self):
        with patch.object(updater,'load_state',return_value=self.state()), patch.object(updater,'check_file_commits',return_value={'rate_limited':True}), self.assertLogs(level='WARNING'):
            self.assertFalse(updater.check_for_updates())

    def test_background_checks_do_not_create_executor_and_stop_between_requests(self):
        stopped=[False]
        def checked(*args):
            stopped[0]=True
            return {'sha':'same'}
        with patch.object(updater,'ThreadPoolExecutor',side_effect=AssertionError('executor during background probe')), patch.object(updater,'check_file_commits',side_effect=checked) as check:
            self.assertFalse(updater.check_for_updates(parallel=False,cancelled=lambda:stopped[0]))
        self.assertEqual(check.call_count,1)
