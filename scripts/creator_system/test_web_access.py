"""Offline injected HTTP checks: never contacts the network or providers."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from creator_system.store import Store, ControlError
from creator_system.sources import register_source
from creator_system.web_access import check_web_source, _head, _PinnedTLS


class WebAccessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root / 'vault')
        self.path = self.root / 'snapshot.txt'
        self.path.write_text('Supplied snapshot. This content is not fetched by the probe.')
        self.register('https://example.org/article')
        self.seen = []

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def register(self, url):
        return register_source(self.store, self.path, 'WEB', url=url)

    def probe(self, transport, resolver=None, **kwargs):
        return check_web_source(self.store, 'WEB', transport=transport,
                                resolver=resolver or (lambda host, port: ['93.184.216.34']), **kwargs)['data']

    def response(self, status, location=None):
        def call(target, timeout):
            self.seen.append(target)
            return {'http_status': status, 'location': location}
        return call

    def test_reachable_only_means_http_head_available(self):
        data = self.probe(self.response(200))
        self.assertEqual(data['status'], 'reachable')
        self.assertFalse(data['body_downloaded'])
        self.assertFalse(data['body_unchanged_verified'])
        self.assertFalse(data['semantic_verified'])
        self.assertEqual(self.seen[0]['ip'], '93.184.216.34')
        self.assertEqual(self.seen[0]['host'], 'example.org')
        receipt = self.store.list('receipt')[-1]
        with self.assertRaises(ControlError):
            self.store.update('receipt', receipt['id'], data, receipt['digest'])

    def test_404_and_410_unavailable_but_403_is_not_deleted(self):
        for code in (404, 410):
            self.assertEqual(self.probe(self.response(code))['status'], 'unavailable')
        for code in (401, 403):
            data = self.probe(self.response(code))
            self.assertEqual(data['status'], 'unknown')
            self.assertEqual(data['reason'], 'access_restricted_not_deleted')

    def test_head_405_has_no_get_fallback(self):
        result = self.probe(self.response(405))
        self.assertEqual(result['status'], 'unknown')
        self.assertEqual(len(self.seen), 1)
        self.assertIn('no_get_fallback', result['reason'])

    def test_timeout_remains_unknown(self):
        def timeout(target, seconds):
            raise TimeoutError()
        self.assertEqual(self.probe(timeout)['status'], 'unknown')
        self.assertEqual(self.probe(timeout)['reason'], 'timeout')

    def test_redirect_loop_and_limit(self):
        def loop(target, timeout):
            return {'http_status': 302, 'location': '/b' if target['request_target'] == '/article' else '/article'}
        self.assertEqual(self.probe(loop)['reason'], 'redirect_loop')
        self.assertEqual(self.probe(self.response(302, '/b'), max_redirects=0)['reason'], 'redirect_limit')

    def test_redirect_private_host_rejected_before_next_transport(self):
        result = self.probe(self.response(302, 'http://127.0.0.1/admin'))
        self.assertEqual(result['status'], 'unknown')
        self.assertTrue(result['reason'].startswith('target_rejected'))
        self.assertEqual(len(self.seen), 1)

    def test_private_literal_localhost_and_credentials_never_transport(self):
        for url in ('http://localhost/', 'http://169.254.169.254/', 'http://10.0.0.1/', 'http://[::1]/', 'https://user:password@example.org/'):
            self.register(url)
            result = self.probe(self.response(200))
            self.assertEqual(result['status'], 'unknown', url)
            self.assertTrue(result['reason'].startswith('target_rejected'), url)
        self.assertEqual(self.seen, [])

    def test_mixed_public_private_dns_rejected(self):
        result = self.probe(self.response(200), resolver=lambda host, port: ['93.184.216.34', '192.168.1.1'])
        self.assertTrue(result['reason'].startswith('target_rejected'))
        self.assertEqual(self.seen, [])

    def test_transport_only_calls_head_and_never_reads_body(self):
        calls = []
        class Response:
            status = 200
            def getheader(self, name): return None
            def read(self): raise AssertionError('Body must never be read')
        class Connection:
            def __init__(self, host, port, timeout): calls.append(('connect', host))
            def request(self, method, target, headers): calls.append((method, headers['Host']))
            def getresponse(self): return Response()
            def close(self): pass
        target = {'scheme':'http','ip':'93.184.216.34','host':'example.org','port':80,'request_target':'/'}
        with patch('creator_system.web_access.http.client.HTTPConnection', Connection):
            self.assertEqual(_head(target, 1)['http_status'], 200)
        self.assertEqual(calls, [('connect','93.184.216.34'),('HEAD','example.org')])

    def test_https_pins_ip_but_verifies_original_tls_hostname(self):
        calls = []
        class Raw:
            def close(self): pass
        class Context:
            def wrap_socket(self, raw, server_hostname):
                calls.append(('tls', server_hostname)); return raw
        target = {'host':'example.org','ip':'93.184.216.34','port':443}
        def connect(address, timeout): calls.append(('connect', address)); return Raw()
        with patch('creator_system.web_access.ssl.create_default_context', return_value=Context()), patch('creator_system.web_access.socket.create_connection', connect):
            connection = _PinnedTLS(target, 1)
            connection.connect()
        self.assertEqual(calls, [('connect',('93.184.216.34',443)),('tls','example.org')])


if __name__ == '__main__':
    unittest.main()
