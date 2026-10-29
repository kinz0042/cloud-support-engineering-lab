"""Worker response classification and retry-delay boundaries."""
import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from app.worker import deliver

ROW = {"id": 1, "order_id": "o", "tenant_id": "acme"}
URL = "http://127.0.0.1:8082/webhook"


def response_error(code, retry=None):
    headers = {} if retry is None else {"Retry-After": retry}
    return HTTPError(URL, code, "test", headers, io.BytesIO())


class RetryClassificationTests(unittest.TestCase):
    def check_error(self, error, expected):
        with patch("app.worker.urlopen", side_effect=error):
            self.assertEqual(deliver(ROW, URL, "secret"), expected)

    def test_numeric_retry_after_is_bounded(self):
        self.check_error(response_error(429, "9999"), (False, "429", 300))

    def test_invalid_retry_after_falls_back(self):
        self.check_error(response_error(429, "not-a-number"), (False, "429", None))

    def test_retry_after_not_applied_to_other_statuses(self):
        self.check_error(response_error(503, "5"), (False, "503", None))

    def test_transport_failure_is_not_misreported_as_http_error(self):
        self.check_error(URLError("connection refused"), (False, "transport_error", None))


if __name__ == "__main__":
    unittest.main()
