import io
import json
import socket
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.oauth_gateway import Handler


class DemoVerifier:
    def validate(self, token):
        return {'tenant_id': 'acme'}


class DemoResponse(io.BytesIO):
    status = 200
    headers = {'X-Request-ID': 'synthetic-upstream-id'}

    def __init__(self, payload=b'{"orders":[],"next_cursor":null}'):
        super().__init__(payload)


class GatewayPaginationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.server.verifier = DemoVerifier()
        cls.server.tenant_keys = {'acme': 'synthetic-api-key'}
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = 'http://127.0.0.1:' + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_query_forwarded_to_fixed_upstream_without_logging_credentials(self):
        with patch('app.oauth_gateway.urlopen', return_value=DemoResponse()) as upstream:
            with self.assertLogs('relaydesk.oauth', level='INFO') as logs:
                req = Request(self.url + '/v1/orders?limit=1&cursor=opaque-demo',
                              headers={'Authorization': 'Bearer demo-token'})
                with urlopen(req, timeout=3) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.headers['X-Upstream-Request-ID'], 'synthetic-upstream-id')
                    self.assertEqual(json.load(response)['orders'], [])
        request = upstream.call_args.args[0]
        self.assertEqual(request.full_url, 'http://api:8081/v1/orders?limit=1&cursor=opaque-demo')
        self.assertEqual(request.get_header('Authorization'), 'Bearer synthetic-api-key')
        self.assertNotIn('demo-token', ' '.join(logs.output))
        self.assertNotIn('opaque-demo', ' '.join(logs.output))

    def test_absolute_form_url_does_not_select_upstream(self):
        with patch('app.oauth_gateway.urlopen') as upstream:
            conn = HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
            try:
                conn.request('GET', 'http://untrusted.invalid/v1/orders?limit=1',
                             headers={'Authorization': 'Bearer demo-token'})
                response = conn.getresponse()
                self.assertEqual(response.status, 404)
                response.read()
            finally:
                conn.close()
            upstream.assert_not_called()

    def test_malformed_absolute_target_is_rejected_without_upstream_call(self):
        with patch('app.oauth_gateway.urlopen') as upstream:
            with socket.create_connection(('127.0.0.1', self.server.server_port), timeout=3) as conn:
                conn.sendall(b'GET http://[broken/v1/orders HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
                with conn.makefile('rb') as response:
                    self.assertIn(b' 400 ', response.readline())
                    response.read()
            upstream.assert_not_called()

    def test_oversized_query_is_rejected_without_upstream_call(self):
        with patch('app.oauth_gateway.urlopen') as upstream:
            req = Request(self.url + '/v1/orders?cursor=' + 'a' * 513,
                          headers={'Authorization': 'Bearer demo-token'})
            with self.assertRaises(HTTPError) as raised:
                urlopen(req, timeout=3)
            with raised.exception as response:
                self.assertEqual(response.code, 400)
                self.assertEqual(json.load(response)['error'], 'invalid_pagination')
            upstream.assert_not_called()

    def test_gateway_accepts_large_valid_page_but_bounds_upstream_body(self):
        payload = json.dumps({'orders': [{'id': str(n), 'external_id': '\U0001f680' * 100}
                                         for n in range(100)], 'next_cursor': None}).encode()
        self.assertGreater(len(payload), 65536)
        with patch('app.oauth_gateway.urlopen', return_value=DemoResponse(payload)):
            req = Request(self.url + '/v1/orders', headers={'Authorization': 'Bearer demo-token'})
            with urlopen(req, timeout=3) as response:
                self.assertEqual(len(json.load(response)['orders']), 100)
        with patch('app.oauth_gateway.urlopen', return_value=DemoResponse(b'x' * (256 * 1024 + 1))):
            req = Request(self.url + '/v1/orders', headers={'Authorization': 'Bearer demo-token'})
            with self.assertRaises(HTTPError) as raised:
                urlopen(req, timeout=3)
            with raised.exception as response:
                self.assertEqual(response.code, 502)
                self.assertEqual(json.load(response)['error'], 'upstream_response_too_large')


if __name__ == '__main__':
    unittest.main()
