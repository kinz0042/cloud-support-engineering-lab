"""Exercise the actual worker and mock partner over loopback HTTP."""
import hashlib
import hmac
import json
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app import partner, worker


class WebhookIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.server = partner.make_server(port=0, secret="test-secret", mode="normal")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/webhook"
        self.row = {"id": 7, "order_id": "order-1", "tenant_id": "acme"}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_successful_delivery_and_duplicate_have_stable_event_id(self):
        self.assertEqual(worker.deliver(self.row, self.url, "test-secret"), (True, "202", None))
        self.assertEqual(worker.deliver(self.row, self.url, "test-secret"), (True, "202", None))
        self.assertEqual(self.server.seen, {"delivery-7"})

    def test_bad_signature_is_rejected_without_recording_event(self):
        self.assertEqual(worker.deliver(self.row, self.url, "wrong-secret"), (False, "401", None))
        self.assertEqual(self.server.seen, set())

    def test_partner_rejection_then_recovery(self):
        self.server.mode = "reject"
        self.assertEqual(worker.deliver(self.row, self.url, "test-secret"), (False, "503", None))
        self.assertEqual(self.server.seen, set())
        self.server.mode = "normal"
        self.assertEqual(worker.deliver(self.row, self.url, "test-secret"), (True, "202", None))
        self.assertEqual(self.server.seen, {"delivery-7"})

    def test_rate_limit_delay_and_recovery(self):
        self.server.mode = "rate_limit"
        self.assertEqual(worker.deliver(self.row, self.url, "test-secret"), (False, "429", 5))
        self.assertEqual(self.server.seen, set())
        self.server.mode = "normal"
        self.assertEqual(worker.deliver(self.row, self.url, "test-secret"), (True, "202", None))

    def test_expired_signed_event_is_rejected(self):
        body = json.dumps({"event_id": "old-event"}).encode()
        timestamp = str(int(time.time()) - 600)
        signature = hmac.new(b"test-secret", timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
        req = Request(self.url, data=body, headers={"X-Relay-Timestamp": timestamp,
                      "X-Relay-Signature": signature}, method="POST")
        with self.assertRaises(HTTPError) as error:
            urlopen(req, timeout=3)
        self.assertEqual(error.exception.code, 401)
        self.assertEqual(self.server.seen, set())


if __name__ == "__main__":
    unittest.main()
