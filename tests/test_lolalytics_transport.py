import unittest
from datetime import datetime, timezone
from email.utils import format_datetime

import requests

from lolalytics.errors import HTTPStatusError, ResponseTooLarge, TransportError
from lolalytics.transport import HTTPTransport


class FakeResponse:
    def __init__(self, status=200, chunks=(b'ok',), headers=None, error=None):
        self.status_code = status
        self.headers = headers or {}
        self.chunks = chunks
        self.error = error
        self.closed = False

    def iter_content(self, chunk_size):
        for chunk in self.chunks:
            if self.error:
                raise self.error
            yield chunk

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []
        self.closed = False

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def close(self):
        self.closed = True


class TransportTests(unittest.TestCase):
    def make_transport(self, results, **kwargs):
        session = FakeSession(results)
        sleeps = []
        clock_state = [100.0]
        def sleep(seconds):
            sleeps.append(seconds)
            clock_state[0] += seconds
        transport = HTTPTransport(session, min_interval=1, sleep=sleep,
                                  clock=lambda: clock_state[0], wall_clock=lambda: 1_700_000_000,
                                  **kwargs)
        return transport, session, sleeps

    def test_success_uses_timeout_stream_and_closes(self):
        response = FakeResponse(chunks=(b'abc', b'def'))
        transport, session, _ = self.make_transport([response])
        self.assertEqual(transport.get('https://lolalytics.com/lol/ahri/build/q-data.json'), b'abcdef')
        self.assertTrue(response.closed)
        self.assertEqual(session.calls[0][1]['timeout'], (5, 20))
        self.assertTrue(session.calls[0][1]['stream'])
        self.assertFalse(session.calls[0][1]['allow_redirects'])

    def test_retries_connection_then_429_retry_after_and_caps_attempts(self):
        response = FakeResponse(status=429, headers={'Retry-After': '2'})
        final = FakeResponse()
        transport, session, sleeps = self.make_transport([requests.ConnectionError(), response, final])
        self.assertEqual(transport.get('https://a1.lolalytics.com/mega/?ep=build'), b'ok')
        self.assertEqual(len(session.calls), 3)
        self.assertTrue(response.closed)
        self.assertIn(2.0, sleeps)
        self.assertIn(1.0, sleeps)

    def test_timeout_retries_but_stops_after_three_attempts(self):
        transport, session, _ = self.make_transport([
            requests.Timeout(), requests.Timeout(), requests.Timeout(), FakeResponse()
        ])
        with self.assertRaises(TransportError):
            transport.get('https://lolalytics.com/lol/ahri/build/q-data.json')
        self.assertEqual(len(session.calls), 3)

    def test_http_date_retry_after(self):
        # Fixed wall clock yields a deterministic delay from the HTTP date.
        target = format_datetime(datetime.fromtimestamp(1_700_000_005, timezone.utc), usegmt=True)
        response = FakeResponse(status=503, headers={'Retry-After': target})
        transport, session, sleeps = self.make_transport([response, FakeResponse()])
        self.assertEqual(transport.get('https://lolalytics.com/lol/ahri/build/q-data.json'), b'ok')
        self.assertIn(5.0, sleeps)
        self.assertTrue(response.closed)

    def test_retry_after_over_limit_fails_without_early_retry(self):
        response = FakeResponse(status=429, headers={'Retry-After': '31'})
        transport, session, _ = self.make_transport([response, FakeResponse()])
        with self.assertRaises(HTTPStatusError) as ctx:
            transport.get('https://lolalytics.com/lol/ahri/build/q-data.json')
        self.assertEqual(ctx.exception.status, 429)
        self.assertEqual(ctx.exception.retry_after, 31)
        self.assertEqual(len(session.calls), 1)
        self.assertTrue(response.closed)

    def test_response_is_closed_before_retry_wait(self):
        response = FakeResponse(status=429, headers={'Retry-After': '2'})
        session = FakeSession([response, FakeResponse()])
        sleeps = []
        def sleep(seconds):
            self.assertTrue(response.closed)
            sleeps.append(seconds)
        transport = HTTPTransport(session, min_interval=0, sleep=sleep)
        self.assertEqual(transport.get('https://lolalytics.com/lol/ahri/build/q-data.json'), b'ok')
        self.assertEqual(sleeps, [2.0])

    def test_nonfinite_retry_after_fails_safely_without_retry(self):
        for header in ('inf', 'nan', '1e999'):
            with self.subTest(header=header):
                response = FakeResponse(status=429, headers={'Retry-After': header})
                transport, session, _ = self.make_transport([response, FakeResponse()])
                with self.assertRaises(HTTPStatusError) as ctx:
                    transport.get('https://lolalytics.com/lol/ahri/build/q-data.json')
                self.assertEqual(ctx.exception.status, 429)
                self.assertEqual(len(session.calls), 1)
                self.assertTrue(response.closed)

    def test_constructor_rejects_invalid_numeric_settings(self):
        for kwargs in (
            {'max_wait': float('inf')}, {'max_wait': float('nan')},
            {'min_interval': float('inf')}, {'min_interval': -1},
            {'timeout': (5, float('inf'))}, {'timeout': (0, 20)},
            {'max_bytes': 0}, {'max_bytes': float('inf')},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                HTTPTransport(FakeSession([]), **kwargs)

    def test_does_not_retry_forbidden_or_redirect(self):
        for status in (403, 302):
            with self.subTest(status=status):
                response = FakeResponse(status=status, headers={'Location': 'https://evil.test/'})
                transport, session, _ = self.make_transport([response])
                with self.assertRaises(HTTPStatusError):
                    transport.get('https://lolalytics.com/lol/ahri/build/q-data.json')
                self.assertEqual(len(session.calls), 1)
                self.assertTrue(response.closed)

    def test_uncompressed_body_limit_and_stream_failure(self):
        response = FakeResponse(chunks=(b'12345',))
        transport, _, _ = self.make_transport([response], max_bytes=4)
        with self.assertRaises(ResponseTooLarge):
            transport.get('https://lolalytics.com/lol/ahri/build/q-data.json')
        self.assertTrue(response.closed)
        broken = FakeResponse(error=ValueError('secret response detail'))
        transport, session, _ = self.make_transport([broken])
        with self.assertRaises(TransportError) as ctx:
            transport.get('https://lolalytics.com/lol/ahri/build/q-data.json')
        self.assertNotIn('secret', str(ctx.exception))
        self.assertEqual(len(session.calls), 1)
        self.assertTrue(broken.closed)

    def test_endpoint_allowlist_rejects_auth_hosts_and_other_paths(self):
        transport, session, _ = self.make_transport([])
        for url in (
            'http://lolalytics.com/lol/ahri/build/q-data.json',
            'https://user:pass@lolalytics.com/lol/ahri/build/q-data.json',
            'https://evil.test/lol/ahri/build/q-data.json',
            'https://lolalytics.com/lol/ahri/build/',
            'https://a1.lolalytics.com/other/',
        ):
            with self.subTest(url=url), self.assertRaises(TransportError):
                transport.get(url)
        self.assertEqual(session.calls, [])

    def test_context_manager_closes_session_and_closed_transport_rejects(self):
        transport, session, _ = self.make_transport([])
        with transport:
            pass
        self.assertTrue(session.closed)
        with self.assertRaises(TransportError):
            transport.get('https://lolalytics.com/lol/ahri/build/q-data.json')


if __name__ == '__main__':
    unittest.main()
