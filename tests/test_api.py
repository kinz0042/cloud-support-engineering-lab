import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from app.server import make_server

class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(0, "test-only-token")
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:" + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, path, token=None):
        headers = {} if token is None else {"Authorization": token}
        try:
            response = urlopen(Request(self.base + path, headers=headers), timeout=3)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.headers, json.load(response)

    def test_health(self):
        self.assertEqual(self.request("/health")[0], 200)

    def test_missing_and_wrong_auth(self):
        for token in (None, "Bearer wrong", "test-only-token", "bearer test-only-token"):
            with self.subTest(token=token):
                status, headers, body = self.request("/v1/orders", token)
                self.assertEqual(status, 401)
                self.assertIn("Bearer", headers["WWW-Authenticate"])
                self.assertEqual(headers["X-Request-ID"], body["request_id"])
                self.assertNotIn("orders", body)

    def test_valid_auth(self):
        status, _, body = self.request("/v1/orders", "Bearer test-only-token")
        self.assertEqual(status, 200)
        self.assertEqual(body["orders"][0]["id"], "ord_demo_001")

    def test_unknown_route(self):
        self.assertEqual(self.request("/does-not-exist")[0], 404)

    def test_logs_do_not_disclose_header_query_or_unknown_path(self):
        with self.assertLogs("support_lab", level="INFO") as captured:
            self.request("/private-customer-name?token=query-secret", "Bearer header-secret")
        logs = " ".join(captured.output)
        for sensitive in ("private-customer-name", "query-secret", "header-secret"):
            self.assertNotIn(sensitive, logs)
        self.assertIn("request_id", logs)

    def test_empty_token_rejected(self):
        with self.assertRaises(ValueError):
            make_server(0, "")
