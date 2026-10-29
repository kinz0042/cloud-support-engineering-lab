import hashlib
import hmac
import json
import threading
import unittest
import uuid
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from app.relay_api import make_server
from app.partner import make_server as make_partner
from app.worker import deliver
from app.relay_store import UnknownOrder


class FakeStore:
    def __init__(self):
        self.available = True
        self.orders = {}
        self.events = set()

    def ready(self):
        return self.available

    def list_orders(self, tenant):
        if not self.available:
            raise RuntimeError("database down")
        return [r for (owner, _), r in self.orders.items() if owner == tenant]

    def create_order(self, tenant, external_id):
        if not self.available:
            raise RuntimeError("database down")
        key = (tenant, external_id)
        if key in self.orders:
            return self.orders[key], False
        order = {"id": str(uuid.uuid4()), "external_id": external_id,
                 "status": "received", "created_at": "2026-10-29T00:00:00Z"}
        self.orders[key] = order
        return order, True

    def record_callback(self, event_id, order_id):
        if not self.available:
            raise RuntimeError("database down")
        fresh = event_id not in self.events
        self.events.add(event_id)
        return fresh


class RelayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = FakeStore()
        cls.server = make_server(0, cls.store, {"acme": "acme-key", "orbit": "orbit-key"}, "test-secret")
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = "http://127.0.0.1:" + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.store.orders.clear()
        self.store.events.clear()
        self.store.available = True

    def call(self, path, method="GET", body=None, headers=None):
        request = Request(self.url + path, data=body, method=method, headers=headers or {})
        try:
            response = urlopen(request, timeout=3)
        except HTTPError as exc:
            response = exc
        with response:
            return response.status, response.headers, json.load(response)

    def test_tenant_isolation_and_idempotent_order(self):
        body = b'{"external_id":"cust-001"}'
        a = {"Authorization": "Bearer acme-key", "Content-Type": "application/json"}
        b = {"Authorization": "Bearer orbit-key", "Content-Type": "application/json"}
        first = self.call("/v1/orders", "POST", body, a)
        second = self.call("/v1/orders", "POST", body, a)
        third = self.call("/v1/orders", "POST", body, b)
        self.assertEqual((first[0], second[0], third[0]), (201, 200, 201))
        self.assertEqual(first[2]["order"]["id"], second[2]["order"]["id"])
        self.assertNotEqual(first[2]["order"]["id"], third[2]["order"]["id"])
        self.assertEqual(len(self.call("/v1/orders", headers=a)[2]["orders"]), 1)
        self.assertEqual(len(self.call("/v1/orders", headers=b)[2]["orders"]), 1)
        self.assertEqual(self.call("/v1/orders")[0], 401)

    def test_readiness_and_dependency_failure(self):
        self.store.available = False
        self.assertEqual(self.call("/health")[0], 200)
        self.assertEqual(self.call("/ready")[0], 503)
        status, headers, body = self.call("/v1/orders", headers={"Authorization": "Bearer acme-key"})
        self.assertEqual(status, 503)
        self.assertEqual(body["request_id"], headers["X-Request-ID"])
        self.assertNotIn("database down", json.dumps(body))
        self.store.available = True
        self.assertEqual(self.call("/ready")[0], 200)

    def test_invalid_json_and_secret_rejected(self):
        status, _, body = self.call("/v1/orders", "POST", b"not-json",
                                    {"Authorization": "Bearer acme-key"})
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "invalid_request")
        self.assertEqual(self.call("/v1/orders", headers={"Authorization": "Bearer wrong"})[0], 401)

    def test_callback_signature_and_duplicate(self):
        order_id = str(uuid.uuid4())
        body = json.dumps({"event_id": "evt-1", "order_id": order_id}).encode()
        signature = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
        self.assertEqual(self.call("/v1/callbacks", "POST", body)[0], 401)
        headers = {"X-Relay-Signature": signature}
        first = self.call("/v1/callbacks", "POST", body, headers)
        second = self.call("/v1/callbacks", "POST", body, headers)
        self.assertEqual(first[0], 202)
        self.assertFalse(first[2]["duplicate"])
        self.assertTrue(second[2]["duplicate"])

    def test_signed_callback_unknown_order_is_not_database_outage(self):
        body = json.dumps({"event_id": "evt-unknown", "order_id": str(uuid.uuid4())}).encode()
        signature = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
        previous = self.store.record_callback
        self.store.record_callback = lambda *_: (_ for _ in ()).throw(UnknownOrder())
        try:
            status, _, response = self.call("/v1/callbacks", "POST", body,
                                            {"X-Relay-Signature": signature})
            self.assertEqual(status, 404)
            self.assertEqual(response["error"], "order_not_found")
        finally:
            self.store.record_callback = previous

    def test_partner_rejects_bad_signature_and_deduplicates(self):
        partner = make_partner(0, "test-secret", "normal")
        thread = threading.Thread(target=partner.serve_forever, daemon=True)
        thread.start()
        try:
            row = {"id": 7, "order_id": str(uuid.uuid4()), "tenant_id": "acme"}
            endpoint = "http://127.0.0.1:" + str(partner.server_port) + "/webhook"
            self.assertEqual(deliver(row, endpoint, "bad-secret")[1], "401")
            self.assertTrue(deliver(row, endpoint, "test-secret")[0])
            self.assertTrue(deliver(row, endpoint, "test-secret")[0])
            self.assertEqual(partner.seen, {"delivery-7"})
        finally:
            partner.shutdown()
            partner.server_close()
            thread.join()
