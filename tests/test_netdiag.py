import socket
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from scripts.netdiag import diagnose


class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
    def log_message(self, *_args):
        pass


class NetworkDiagnosticTests(unittest.TestCase):
    def test_local_http_success(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), Health)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = diagnose('127.0.0.1', server.server_port)
            self.assertTrue(result['checks']['dns']['ok'])
            self.assertTrue(result['checks']['tcp']['ok'])
            self.assertEqual(result['checks']['http']['status'], 200)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_bad_dns_is_identified_before_connection(self):
        result = diagnose('bad-name.invalid', 80)
        self.assertFalse(result['checks']['dns']['ok'])
        self.assertNotIn('tcp', result['checks'])

    def test_tls_handshake_failure_does_not_disable_verification(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), Health)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = diagnose('127.0.0.1', server.server_port, tls=True, timeout=3)
            self.assertTrue(result['checks']['tcp']['ok'])
            self.assertFalse(result['checks']['tls']['ok'])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_header_injection_rejected(self):
        with self.assertRaises(ValueError):
            diagnose('localhost\r\nX-Injected: yes', 80)
