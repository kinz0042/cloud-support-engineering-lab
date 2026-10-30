import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from scripts.paginate_orders import PaginationError, collect


class FakeAPI(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        target = urlsplit(self.path)
        if target.path == '/capture':
            self.server.redirect_followed = True
            self.send_response(200)
            self.end_headers()
            return
        if self.headers.get('Authorization') != 'Bearer public-demo':
            self.send_response(401)
            self.end_headers()
            return
        if self.server.mode == 'redirect':
            self.send_response(302)
            self.send_header('Location', f'http://127.0.0.1:{self.server.server_port}/capture')
            self.end_headers()
            return
        if self.server.mode == 'oversized':
            self.send_response(200)
            self.send_header('Content-Length', str(256 * 1024 + 1))
            self.end_headers()
            return
        if self.server.mode == 'oversized_without_length':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'x' * (256 * 1024 + 1))
            return
        if self.server.mode == 'incomplete':
            data = b'{"orders":[],"next_cursor":null}'
            self.send_response(200)
            self.send_header('Content-Length', str(len(data) + 3))
            self.end_headers()
            self.wfile.write(data)
            return
        query = parse_qs(target.query)
        cursor = query.get('cursor', [None])[0]
        if self.server.mode == 'large':
            body = {'orders': [{'id': str(n), 'external_id': '\U0001f680' * 100} for n in range(100)],
                    'next_cursor': None}
        elif self.server.mode == 'cycle':
            body = {'orders': [{'id': 'a' if not cursor else 'b'}], 'next_cursor': 'repeat'}
        elif self.server.mode == 'duplicate':
            body = {'orders': [{'id': 'a'}], 'next_cursor': 'next' if not cursor else None}
        else:
            body = {'orders': [{'id': 'a'}, {'id': 'b'}] if not cursor else [{'id': 'c'}],
                    'next_cursor': 'next' if not cursor else None}
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class PagingClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), FakeAPI)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}/v1/orders'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.server.mode = 'normal'
        self.server.redirect_followed = False

    def test_collects_all_pages(self):
        self.assertEqual(collect(self.url, 'public-demo', limit=2), {'pages': 2, 'orders': 3})

    def test_repeated_cursors_and_duplicate_records_stop(self):
        for mode in ('cycle', 'duplicate'):
            self.server.mode = mode
            with self.subTest(mode=mode), self.assertRaises(PaginationError):
                collect(self.url, 'public-demo', limit=2)

    def test_redirects_are_not_followed(self):
        self.server.mode = 'redirect'
        with self.assertRaisesRegex(PaginationError, 'HTTP 302'):
            collect(self.url, 'public-demo')
        self.assertFalse(self.server.redirect_followed)

    def test_wrong_credential_and_nonlocal_url_fail(self):
        with self.assertRaisesRegex(PaginationError, 'HTTP 401') as error:
            collect(self.url, 'wrong-demo-key')
        self.assertNotIn('wrong-demo-key', str(error.exception))
        with self.assertRaises(PaginationError):
            collect('http://example.com:8081/v1/orders', 'public-demo')

    def test_large_valid_page_is_supported_with_bounded_response(self):
        self.server.mode = 'large'
        self.assertEqual(collect(self.url, 'public-demo', limit=100), {'pages': 1, 'orders': 100})
        for mode in ('oversized', 'oversized_without_length'):
            self.server.mode = mode
            with self.subTest(mode=mode), self.assertRaisesRegex(PaginationError, 'response limit'):
                collect(self.url, 'public-demo', limit=100)

    def test_truncated_response_is_not_treated_as_success(self):
        self.server.mode = 'incomplete'
        with self.assertRaisesRegex(PaginationError, 'incomplete response'):
            collect(self.url, 'public-demo')


if __name__ == '__main__':
    unittest.main()
