import hashlib
import hmac
import json
import threading
import unittest
import uuid
import time
from datetime import datetime
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from app.relay_api import make_server
from app.pagination import encode_cursor
from app.partner import make_server as make_partner
from app.worker import deliver
from app.relay_store import UnknownOrder, CallbackConflict, StoreQueryCanceled
from app.request_metrics import RequestDurations
from scripts.paginate_orders import collect
from unittest.mock import patch


class FakeStore:
    def __init__(self):
        self.available = True
        self.orders = {}
        self.events = {}

    def ready(self):
        return self.available

    def delivery_metrics(self):
        return {"counts": {"pending": 3, "leased": 1, "delivered": 4, "dead": 2},
                "oldest_due_seconds": 42.0}

    def list_orders(self, tenant, limit=100, cursor=None):
        if not self.available:
            raise RuntimeError("database down")
        def ordering(row):
            return datetime.fromisoformat(row["created_at"]), uuid.UUID(row["id"])
        rows = sorted((r for (owner, _), r in self.orders.items() if owner == tenant),
                      key=ordering, reverse=True)
        if cursor:
            boundary = cursor[0], uuid.UUID(cursor[1])
            rows = [row for row in rows if ordering(row) < boundary]
        return rows[:limit + 1]

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
        if event_id in self.events:
            if self.events[event_id] != order_id:
                raise CallbackConflict()
            return False
        self.events[event_id] = order_id
        return True


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

    def test_pagination_retrieves_ties_and_preserves_tenant_scope(self):
        for n in range(105):
            self.store.create_order("acme", f"acme-page-{n}")
        for n in range(4):
            self.store.create_order("orbit", f"orbit-page-{n}")
        auth = {"Authorization": "Bearer acme-key"}
        status, _, first = self.call("/v1/orders", headers=auth)
        self.assertEqual(status, 200)
        self.assertEqual(len(first["orders"]), 100)
        self.assertTrue(first["next_cursor"])
        status, _, last = self.call("/v1/orders?" + urlencode({"cursor": first["next_cursor"]}), headers=auth)
        self.assertEqual(status, 200)
        self.assertEqual(len(last["orders"]), 5)
        self.assertIsNone(last["next_cursor"])
        ids = [row["id"] for row in first["orders"] + last["orders"]]
        self.assertEqual(len(set(ids)), 105)
        self.assertEqual(collect(self.url + '/v1/orders', 'acme-key', limit=25), {'pages': 5, 'orders': 105})
        # A forged high boundary includes every Orbit fixture but must not expose Acme rows.
        boundary = encode_cursor({"created_at": first["orders"][0]["created_at"],
                                  "id": str(uuid.UUID(int=(1 << 128) - 1))})
        status, _, orbit = self.call("/v1/orders?" + urlencode({"cursor": boundary}),
                                     headers={"Authorization": "Bearer orbit-key"})
        self.assertEqual(status, 200)
        self.assertEqual(len(orbit["orders"]), 4)
        self.assertTrue(all(row["external_id"].startswith("orbit-page-") for row in orbit["orders"]))
        self.assertFalse(set(ids) & {row["id"] for row in orbit["orders"]})

    def test_invalid_pagination_does_not_reach_store_or_bypass_auth(self):
        auth = {"Authorization": "Bearer acme-key"}
        paths = ("/v1/orders?limit=0", "/v1/orders?limit=101", "/v1/orders?limit=1&limit=2",
                 "/v1/orders?cursor=", "/v1/orders?cursor=bad!", "/v1/orders?unexpected=1")
        with patch.object(self.store, "list_orders", wraps=self.store.list_orders) as list_orders:
            for path in paths:
                with self.subTest(path=path):
                    status, _, body = self.call(path, headers=auth)
                    self.assertEqual((status, body["error"]), (400, "invalid_pagination"))
            list_orders.assert_not_called()
        self.assertEqual(self.call("/v1/orders?limit=0")[0], 401)
        with self.assertLogs('relaydesk', level='INFO') as logs:
            self.assertEqual(self.call('/v1/orders?cursor=private-cursor-marker', headers=auth)[0], 400)
        self.assertNotIn('private-cursor-marker', ' '.join(logs.output))
        self.assertNotIn('acme-key', ' '.join(logs.output))

    def test_metrics_report_database_readiness_without_secrets(self):
        self.call("/v1/orders", headers={"Authorization": "Bearer acme-key"})
        self.store.available = False
        with urlopen(self.url + "/metrics", timeout=3) as response:
            metrics = response.read().decode()
        self.assertIn("relaydesk_database_ready 0", metrics)
        self.assertIn('relaydesk_requests_total{route="/v1/orders",status="200"}', metrics)
        self.assertNotIn("acme-key", metrics)
        self.store.available = True
        with urlopen(self.url + "/metrics", timeout=3) as response:
            self.assertIn("relaydesk_database_ready 1", response.read().decode())

    def test_invalid_json_and_secret_rejected(self):
        status, _, body = self.call("/v1/orders", "POST", b"not-json",
                                    {"Authorization": "Bearer acme-key"})
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "invalid_request")
        self.assertEqual(self.call("/v1/orders", headers={"Authorization": "Bearer wrong"})[0], 401)

    def test_latency_histogram_and_log_use_the_same_processing_duration(self):
        self.server.request_durations = RequestDurations()
        clock = self.server.clock
        ticks = iter((100.0, 100.75))
        self.server.clock = lambda: next(ticks)
        try:
            with self.assertLogs('relaydesk', level='INFO') as logs:
                self.assertEqual(self.call('/v1/orders', headers={'Authorization': 'Bearer acme-key'})[0], 200)
        finally:
            self.server.clock = clock
        self.assertIn('"duration_ms": 750.0', logs.output[0])
        with urlopen(self.url + '/metrics', timeout=3) as response:
            metrics = response.read().decode()
        self.assertIn('relaydesk_request_duration_seconds_bucket{route="/v1/orders",le="0.5"} 0', metrics)
        self.assertIn('relaydesk_request_duration_seconds_bucket{route="/v1/orders",le="1"} 1', metrics)
        self.assertIn('relaydesk_request_duration_seconds_sum{route="/v1/orders"} 0.75', metrics)

    def test_query_cancellation_is_correlated_without_exposing_database_details(self):
        with patch.object(self.store, 'list_orders', side_effect=StoreQueryCanceled('private-query')):
            status, headers, body = self.call('/v1/orders', headers={'Authorization': 'Bearer acme-key'})
        self.assertEqual(status, 503)
        self.assertEqual(body['error'], 'dependency_query_canceled')
        self.assertEqual(body['request_id'], headers['X-Request-ID'])
        self.assertNotIn('private-query', json.dumps(body))

    def test_queue_metrics_are_bounded_and_do_not_contain_event_or_tenant_labels(self):
        with urlopen(self.url + "/metrics", timeout=3) as response:
            metrics = response.read().decode()
        self.assertIn('relaydesk_deliveries{state="dead"} 2', metrics)
        self.assertIn('relaydesk_deliveries{state="pending"} 3', metrics)
        self.assertIn("relaydesk_delivery_metrics_available 1", metrics)
        self.assertIn("relaydesk_oldest_due_delivery_age_seconds 42.0", metrics)
        for private_label in ("tenant_id", "event_id", "acme-key"):
            self.assertNotIn(private_label, metrics)

    def test_failed_queue_collection_is_not_exported_as_zero_backlog(self):
        with patch.object(self.store, "delivery_metrics", side_effect=RuntimeError("private-db-secret")):
            with urlopen(self.url + "/metrics", timeout=3) as response:
                metrics = response.read().decode()
        self.assertIn("relaydesk_database_ready 1", metrics)
        self.assertIn("relaydesk_delivery_metrics_available 0", metrics)
        self.assertNotIn('relaydesk_deliveries{', metrics)
        self.assertFalse(any(line.startswith("relaydesk_oldest_due_delivery_age_seconds ")
                             for line in metrics.splitlines()))
        self.assertNotIn("private-db-secret", metrics)

    def test_database_outage_does_not_attempt_another_queue_connection(self):
        self.store.available = False
        with patch.object(self.store, "delivery_metrics") as collect:
            with urlopen(self.url + "/metrics", timeout=3) as response:
                metrics = response.read().decode()
        collect.assert_not_called()
        self.assertIn("relaydesk_database_ready 0", metrics)
        self.assertIn("relaydesk_delivery_metrics_available 0", metrics)
        self.assertNotIn('relaydesk_deliveries{', metrics)

    def test_callback_signature_and_duplicate(self):
        order_id = str(uuid.uuid4())
        body = json.dumps({"event_id": "evt-1", "order_id": order_id}).encode()
        timestamp = str(int(time.time()))
        signature = hmac.new(b"test-secret", timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
        self.assertEqual(self.call("/v1/callbacks", "POST", body)[0], 401)
        headers = {"X-Relay-Signature": signature, "X-Relay-Timestamp": timestamp}
        first = self.call("/v1/callbacks", "POST", body, headers)
        second = self.call("/v1/callbacks", "POST", body, headers)
        self.assertEqual(first[0], 202)
        self.assertFalse(first[2]["duplicate"])
        self.assertTrue(second[2]["duplicate"])

    def test_event_id_reused_for_another_order_returns_conflict(self):
        timestamp = str(int(time.time()))
        def signed(order_id):
            body = json.dumps({"event_id": "evt-shared", "order_id": order_id}).encode()
            signature = hmac.new(b"test-secret", timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
            return self.call("/v1/callbacks", "POST", body,
                             {"X-Relay-Signature": signature, "X-Relay-Timestamp": timestamp})
        self.assertEqual(signed(str(uuid.uuid4()))[0], 202)
        conflict = signed(str(uuid.uuid4()))
        self.assertEqual(conflict[0], 409)
        self.assertEqual(conflict[2]["error"], "event_id_conflict")

    def test_signed_callback_unknown_order_is_not_database_outage(self):
        body = json.dumps({"event_id": "evt-unknown", "order_id": str(uuid.uuid4())}).encode()
        timestamp = str(int(time.time()))
        signature = hmac.new(b"test-secret", timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
        previous = self.store.record_callback
        self.store.record_callback = lambda *_: (_ for _ in ()).throw(UnknownOrder())
        try:
            status, _, response = self.call("/v1/callbacks", "POST", body,
                                            {"X-Relay-Signature": signature, "X-Relay-Timestamp": timestamp})
            self.assertEqual(status, 404)
            self.assertEqual(response["error"], "order_not_found")
        finally:
            self.store.record_callback = previous

    def test_stale_signed_callback_rejected(self):
        body = json.dumps({"event_id": "evt-stale", "order_id": str(uuid.uuid4())}).encode()
        timestamp = str(int(time.time()) - 3600)
        signature = hmac.new(b"test-secret", timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
        status, _, response = self.call("/v1/callbacks", "POST", body,
                                        {"X-Relay-Signature": signature, "X-Relay-Timestamp": timestamp})
        self.assertEqual(status, 401)
        self.assertEqual(response["error"], "invalid_signature")

    def test_invalid_callback_headers_are_rejected(self):
        body = json.dumps({"event_id": "evt-invalid", "order_id": str(uuid.uuid4())}).encode()
        for timestamp, signature in [("9" * 100, "abcd"), (str(int(time.time())), "é")]:
            with self.subTest(timestamp=timestamp, signature=signature):
                status, _, _ = self.call("/v1/callbacks", "POST", body,
                                         {"X-Relay-Timestamp": timestamp, "X-Relay-Signature": signature})
                self.assertEqual(status, 401)

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

    def test_partner_rate_limit_gives_bounded_retry_delay(self):
        partner = make_partner(0, "test-secret", "rate_limit")
        thread = threading.Thread(target=partner.serve_forever, daemon=True)
        thread.start()
        try:
            row = {"id": 8, "order_id": str(uuid.uuid4()), "tenant_id": "acme"}
            endpoint = "http://127.0.0.1:" + str(partner.server_port) + "/webhook"
            self.assertEqual(deliver(row, endpoint, "test-secret"), (False, "429", 5))
            self.assertEqual(partner.seen, set())
        finally:
            partner.shutdown()
            partner.server_close()
            thread.join()


