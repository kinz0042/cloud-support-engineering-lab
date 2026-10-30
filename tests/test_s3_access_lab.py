import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from scripts.s3_access_lab import decide_get, load_policy, make_server


class S3AccessLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.broken = make_server(0, "broken")
        cls.recovered = make_server(0, "recovered")
        cls.threads = []
        for server in (cls.broken, cls.recovered):
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            cls.threads.append(thread)

    @classmethod
    def tearDownClass(cls):
        for server, thread in zip((cls.broken, cls.recovered), cls.threads):
            server.shutdown()
            server.server_close()
            thread.join()

    def request(self, server, path, principal="integration-demo"):
        headers = {} if principal is None else {"X-Lab-Principal": principal}
        url = f"http://127.0.0.1:{server.server_port}{path}"
        try:
            response = urlopen(Request(url, headers=headers), timeout=3)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.headers, json.load(response)

    def test_health_does_not_prove_report_access(self):
        self.assertEqual(self.request(self.broken, "/health", principal=None)[0], 200)
        status, headers, body = self.request(self.broken, "/v1/get?" + urlencode({"key": "reports/settlement-demo.json"}))
        self.assertEqual(status, 403)
        self.assertEqual(body["error"], "AccessDenied")
        self.assertEqual(headers["X-Request-ID"], body["request_id"])

    def test_separate_list_and_get_permissions(self):
        self.assertEqual(self.request(self.broken, "/v1/list?prefix=allowed%2F")[0], 200)
        self.assertEqual(self.request(self.broken, "/v1/get?key=allowed%2Freadme.txt")[0], 200)
        self.assertEqual(self.request(self.broken, "/v1/list?prefix=reports%2F")[0], 403)

    def test_scoped_recovery_and_negative_controls(self):
        key = "reports/settlement-demo.json"
        path = "/v1/get?" + urlencode({"key": key})
        self.assertEqual(self.request(self.broken, path)[0], 403)
        self.assertEqual(self.request(self.recovered, path)[0], 200)
        self.assertEqual(self.request(self.recovered, "/v1/get?key=allowed%2Freadme.txt")[0], 200)
        self.assertEqual(self.request(self.recovered, "/v1/get?key=reports%2Fother-demo.json")[0], 403)
        self.assertEqual(self.request(self.recovered, "/v1/get?key=private%2Fpayroll-demo.json")[0], 403)
        self.assertEqual(self.request(self.recovered, "/v1/list?prefix=reports%2F")[0], 403)

    def test_explicit_toy_deny_takes_precedence_over_toy_allow(self):
        policy = load_policy("recovered")
        policy["allow_get_exact"].append("private/payroll-demo.json")
        self.assertEqual(decide_get(policy, "private/payroll-demo.json"), (False, "explicit_toy_deny"))

    def test_unknown_or_missing_demo_principal_is_rejected(self):
        self.assertEqual(self.request(self.broken, "/v1/policy", principal=None)[0], 401)
        self.assertEqual(self.request(self.broken, "/v1/policy", principal="someone-else")[0], 401)
        self.assertEqual(self.request(self.broken, "/v1/policy")[2]["toy_policy"]["label"], "broken")

    def test_invalid_or_duplicate_query_parameters(self):
        for path in ("/v1/get", "/v1/get?key=", "/v1/get?key=a&key=b", "/v1/get?key=a&extra=b"):
            with self.subTest(path=path):
                self.assertEqual(self.request(self.broken, path)[0], 400)

    def test_logs_omit_headers_and_raw_urls(self):
        with self.assertLogs("s3_access_lab", level="INFO") as captured:
            self.request(self.broken, "/secret-customer?token=secret-query", principal="secret-header")
        output = " ".join(captured.output)
        for value in ("secret-customer", "secret-query", "secret-header"):
            self.assertNotIn(value, output)
        self.assertIn("request_id", output)

    def test_loopback_binding_and_invalid_fixture(self):
        self.assertEqual(self.broken.server_address[0], "127.0.0.1")
        with self.assertRaises(ValueError):
            load_policy("not-a-phase")


if __name__ == "__main__":
    unittest.main()
