"""Verify worker destination boundaries using local HTTP servers."""
import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.worker import deliver

ROW = {"id": 13, "order_id": "synthetic-order", "tenant_id": "acme"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def handle_request(self):
        self.server.requests.append((self.command, self.path, dict(self.headers)))
        if self.command == "POST":
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
        self.send_response(self.server.status)
        if self.server.location:
            self.send_header("Location", self.server.location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_POST = handle_request
    do_GET = handle_request


class LocalServer:
    def __init__(self, status=202, location=None):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.status, self.server.location, self.server.requests = status, location, []
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/webhook"

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


class DestinationTests(unittest.TestCase):
    def test_redirects_fail_without_forwarding_signed_headers(self):
        target = LocalServer()
        self.addCleanup(target.close)
        original = LocalServer(location=target.url)
        self.addCleanup(original.close)
        for code in (301, 302, 303, 307, 308):
            with self.subTest(code=code):
                original.server.status = code
                self.assertEqual(deliver(ROW, original.url, "synthetic-secret"), (False, str(code), None))
        self.assertEqual(len(original.server.requests), 5)
        self.assertTrue(all(req[0] == "POST" and "X-Relay-Signature" in req[2]
                            for req in original.server.requests))
        self.assertEqual(target.server.requests, [])

    def test_successful_partner_response_still_succeeds(self):
        partner = LocalServer()
        self.addCleanup(partner.close)
        self.assertEqual(deliver(ROW, partner.url, "synthetic-secret"), (True, "202", None))
        self.assertEqual(len(partner.server.requests), 1)

    def test_ambient_http_proxy_is_not_used(self):
        partner = LocalServer()
        proxy = LocalServer()
        self.addCleanup(partner.close)
        self.addCleanup(proxy.close)
        env = dict(os.environ, http_proxy=proxy.url, HTTP_PROXY=proxy.url, no_proxy="", NO_PROXY="")
        code = ("import json, sys; from app.worker import deliver; "
                "print(json.dumps(deliver(json.loads(sys.argv[1]), sys.argv[2], 'synthetic-secret'))) ")
        result = subprocess.run([sys.executable, "-c", code, json.dumps(ROW), partner.url],
                                env=env, capture_output=True, text=True, timeout=10, check=True)
        self.assertEqual(json.loads(result.stdout), [True, "202", None])
        self.assertEqual(len(partner.server.requests), 1)
        self.assertEqual(proxy.server.requests, [])


if __name__ == "__main__":
    unittest.main()
