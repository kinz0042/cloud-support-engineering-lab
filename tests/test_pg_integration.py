"""Real PostgreSQL contract, enabled only when DATABASE_URL is supplied."""
import os
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode
import json
import time
from concurrent.futures import ThreadPoolExecutor

from app.relay_api import make_server
from app.pagination import encode_cursor
from app import relay_store
from app.partner import make_server as make_partner
from app.worker import deliver


@unittest.skipUnless(os.getenv("DATABASE_URL"), "PostgreSQL URL not supplied")
class PostgreSQLIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
            for statement in Path("db/init.sql").read_text().split(";"):
                if statement.strip():
                    conn.execute(statement)
        cls.api = make_server(0, relay_store, {"acme": "ci-acme", "orbit": "ci-orbit"}, "ci-secret")
        cls.thread = threading.Thread(target=cls.api.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = "http://127.0.0.1:" + str(cls.api.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.api.shutdown()
        cls.api.server_close()
        cls.thread.join()

    def call(self, path, method="GET", body=None, token=None):
        headers = {} if token is None else {"Authorization": "Bearer " + token}
        request = Request(self.url + path, data=body, method=method, headers=headers)
        try:
            response = urlopen(request, timeout=3)
        except HTTPError as exc:
            response = exc
        with response:
            return response.status, json.load(response)

    def setUp(self):
        # DATABASE_URL must point at a disposable integration-test database.
        with relay_store._connect() as conn:
            conn.execute("TRUNCATE delivery_replay_audit, received_events, deliveries, orders RESTART IDENTITY")

    def exhaust_delivery(self):
        order, _ = relay_store.create_order("acme", "replay-fixture")
        for attempt in range(1, 6):
            row = relay_store.claim_delivery()
            self.assertEqual(row["attempts"], attempt)
            state = relay_store.finish_delivery(row["id"], attempt, False, "503", retry_delay=0)
            self.assertEqual(state, "dead" if attempt == 5 else "pending")
        return row

    def replay(self, row, **kwargs):
        return relay_store.replay_delivery(row["id"], "acme", row["attempts"],
                                           "ci-operator", "INC-015 recipient reviewed", True, **kwargs)

    def test_dead_delivery_replay_preserves_id_and_fences_old_worker(self):
        row = self.exhaust_delivery()
        before = relay_store.inspect_delivery(row["id"], "acme")
        self.assertEqual(before["state"], "dead")
        replayed = self.replay(row)
        self.assertEqual(replayed["attempts"], 5)
        self.assertEqual(replayed["max_attempts"], 10)
        current = relay_store.claim_delivery()
        self.assertEqual(current["attempts"], 6)
        self.assertEqual(current["id"], row["id"])
        with self.assertRaises(relay_store.LeaseLost):
            relay_store.finish_delivery(row["id"], 5, True)
        self.assertEqual(relay_store.finish_delivery(current["id"], 6, True), "delivered")
        after = relay_store.inspect_delivery(row["id"], "acme")
        self.assertEqual(before["event_id"], after["event_id"])
        self.assertEqual(len(after["replays"]), 1)
        self.assertEqual(after["replays"][0]["previous_attempts"], 5)
        self.assertIsNone(relay_store.inspect_delivery(row["id"], "orbit"))
        with self.assertRaises(relay_store.ReplayRejected):
            self.replay(row)

    def test_queue_metrics_distinguish_dead_future_due_and_expired_lease(self):
        empty = relay_store.delivery_metrics()
        self.assertEqual(sum(empty["counts"].values()), 0)
        self.assertEqual(empty["oldest_due_seconds"], 0)
        row = self.exhaust_delivery()
        dead = relay_store.delivery_metrics()
        self.assertEqual(dead["counts"]["dead"], 1)
        self.assertEqual(dead["oldest_due_seconds"], 0)
        self.replay(row)
        with relay_store._connect() as conn:
            conn.execute("UPDATE deliveries SET next_attempt_at=now()+interval '1 hour' WHERE id=%s", (row["id"],))
        future = relay_store.delivery_metrics()
        self.assertEqual(future["counts"]["pending"], 1)
        self.assertEqual(future["oldest_due_seconds"], 0)
        with relay_store._connect() as conn:
            conn.execute("UPDATE deliveries SET next_attempt_at=now()-interval '20 seconds' WHERE id=%s", (row["id"],))
        self.assertGreaterEqual(relay_store.delivery_metrics()["oldest_due_seconds"], 20)
        current = relay_store.claim_delivery()
        self.assertEqual(relay_store.delivery_metrics()["oldest_due_seconds"], 0)
        with relay_store._connect() as conn:
            conn.execute("UPDATE deliveries SET lease_until=now()-interval '40 seconds' WHERE id=%s", (row["id"],))
        expired = relay_store.delivery_metrics()
        self.assertEqual(expired["counts"]["leased"], 1)
        self.assertGreaterEqual(expired["oldest_due_seconds"], 40)
        relay_store.finish_delivery(current["id"], current["attempts"], True)
        recovered = relay_store.delivery_metrics()
        self.assertEqual(recovered["counts"]["delivered"], 1)
        self.assertEqual(recovered["oldest_due_seconds"], 0)

    def test_order_read_lock_wait_is_bounded_and_recovers(self):
        relay_store.create_order('acme', 'blocked-read-fixture')
        with relay_store._connect() as locker:
            locker.execute('LOCK TABLE orders IN ACCESS EXCLUSIVE MODE')
            self.assertEqual(self.call('/health')[0], 200)
            self.assertEqual(self.call('/ready')[0], 200)
            started = time.perf_counter()
            status, body = self.call('/v1/orders', token='ci-acme')
            duration = time.perf_counter() - started
            self.assertEqual(status, 503)
            self.assertEqual(body['error'], 'dependency_query_canceled')
            self.assertGreaterEqual(duration, 1.5)
        self.assertEqual(self.call('/v1/orders', token='ci-acme')[0], 200)

    def test_replay_is_bounded_and_concurrent_requests_do_not_double_replay(self):
        row = self.exhaust_delivery()
        with self.assertRaises(relay_store.ReplayRejected):
            relay_store.replay_delivery(row["id"], "orbit", 5, "ci", "wrong tenant denied", True)
        with self.assertRaises(relay_store.ReplayRejected):
            relay_store.replay_delivery(row["id"], "acme", 4, "ci", "stale observation denied", True)
        def request_replay(_):
            try:
                self.replay(row)
                return "accepted"
            except relay_store.ReplayRejected:
                return "rejected"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(request_replay, range(2)))
        self.assertCountEqual(results, ["accepted", "rejected"])
        for attempt in range(6, 11):
            current = relay_store.claim_delivery()
            self.assertEqual(current["attempts"], attempt)
            state = relay_store.finish_delivery(current["id"], attempt, False, "503", retry_delay=0)
            self.assertEqual(state, "dead" if attempt == 10 else "pending")
        self.assertIsNone(relay_store.claim_delivery())
        self.assertEqual(len(relay_store.inspect_delivery(row["id"], "acme")["replays"]), 1)

    def test_failed_audit_write_rolls_back_requeue(self):
        from psycopg.errors import CheckViolation
        row = self.exhaust_delivery()
        with relay_store._connect() as conn:
            conn.execute("ALTER TABLE delivery_replay_audit ADD CONSTRAINT ci_deny_audit CHECK (actor <> 'ci-operator')")
        try:
            with self.assertRaises(CheckViolation):
                self.replay(row)
            after = relay_store.inspect_delivery(row["id"], "acme")
            self.assertEqual((after["state"], after["max_attempts"], after["replays"]), ("dead", 5, []))
        finally:
            with relay_store._connect() as conn:
                conn.execute("ALTER TABLE delivery_replay_audit DROP CONSTRAINT ci_deny_audit")

    def test_existing_database_migration_can_be_repeated_without_data_loss(self):
        row = self.exhaust_delivery()
        with relay_store._connect() as conn:
            conn.execute("DROP TABLE delivery_replay_audit")
            conn.execute("ALTER TABLE deliveries DROP COLUMN max_attempts")
        import psycopg
        for _ in range(2):
            with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
                conn.execute(Path("db/migrations/001_delivery_replay.sql").read_text())
        after = relay_store.inspect_delivery(row["id"], "acme")
        self.assertEqual((after["attempts"], after["max_attempts"], after["state"]), (5, 5, "dead"))
        self.replay(row)

    def test_database_outbox_tenants_and_delivery(self):
        import psycopg
        self.assertEqual(self.call("/ready")[0], 200)
        payload = b'{"external_id":"ci-order"}'
        created, body = self.call("/v1/orders", "POST", payload, "ci-acme")
        self.assertEqual(created, 201)
        order_id = body["order"]["id"]
        self.assertEqual(self.call("/v1/orders", "POST", payload, "ci-acme")[0], 200)
        self.assertEqual(self.call("/v1/orders", "POST", payload, "ci-orbit")[0], 201)
        self.assertEqual(len(self.call("/v1/orders", token="ci-acme")[1]["orders"]), 1)
        self.assertEqual(len(self.call("/v1/orders", token="ci-orbit")[1]["orders"]), 1)
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM deliveries").fetchone()[0], 2)
        row = relay_store.claim_delivery()
        self.assertEqual(row["order_id"], order_id)
        # Simulate an expired lease while a worker is delayed, then claim again.
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
            conn.execute("UPDATE deliveries SET lease_until=now()-interval '1 second' WHERE id=%s", (row["id"],))
            # Keep the second fixture out of the due queue for this assertion.
            conn.execute("UPDATE deliveries SET next_attempt_at=now()+interval '1 hour' WHERE id<>%s", (row["id"],))
        current = relay_store.claim_delivery()
        self.assertEqual(current["id"], row["id"])
        self.assertEqual(current["attempts"], row["attempts"] + 1)
        with self.assertRaises(relay_store.LeaseLost):
            relay_store.finish_delivery(row["id"], row["attempts"], False, "stale")
        row = current
        partner = make_partner(0, "ci-secret", "normal")
        worker = threading.Thread(target=partner.serve_forever, daemon=True)
        worker.start()
        try:
            endpoint = "http://127.0.0.1:" + str(partner.server_port) + "/webhook"
            success, code, retry = deliver(row, endpoint, "ci-secret")
            self.assertEqual((success, code, retry), (True, "202", None))
            self.assertEqual(relay_store.finish_delivery(row["id"], row["attempts"], True), "delivered")
            with self.assertRaises(relay_store.LeaseLost):
                relay_store.finish_delivery(row["id"], row["attempts"], False, "late-worker")
            self.assertEqual(partner.seen, {"delivery-" + str(row["id"])})
        finally:
            partner.shutdown()
            partner.server_close()
            worker.join()
        self.assertTrue(relay_store.record_callback("ci-event", order_id))
        self.assertFalse(relay_store.record_callback("ci-event", order_id))
        other_order = self.call("/v1/orders", token="ci-orbit")[1]["orders"][0]["id"]
        with self.assertRaises(relay_store.CallbackConflict):
            relay_store.record_callback("ci-event", other_order)
        self.assertFalse(relay_store.record_callback("ci-event", order_id))

    def test_paginated_orders_with_equal_timestamps_and_tenant_isolation(self):
        # Direct inserts are disposable test fixtures and intentionally skip the outbox.
        with relay_store._connect() as conn:
            conn.execute("INSERT INTO orders (id, tenant_id, external_id, created_at) "
                         "SELECT gen_random_uuid(), 'acme', 'page-acme-' || n, "
                         "TIMESTAMPTZ '2026-01-01 00:00:00+00' FROM generate_series(1, 105) n")
            conn.execute("INSERT INTO orders (id, tenant_id, external_id, created_at) "
                         "SELECT gen_random_uuid(), 'orbit', 'page-orbit-' || n, "
                         "TIMESTAMPTZ '2026-01-01 00:00:00+00' FROM generate_series(1, 4) n")
        status, first = self.call('/v1/orders', token='ci-acme')
        self.assertEqual(status, 200)
        self.assertEqual(len(first['orders']), 100)
        self.assertTrue(first['next_cursor'])
        status, last = self.call('/v1/orders?' + urlencode({'cursor': first['next_cursor']}), token='ci-acme')
        self.assertEqual(status, 200)
        self.assertEqual(len(last['orders']), 5)
        self.assertIsNone(last['next_cursor'])
        ids = [row['id'] for row in first['orders'] + last['orders']]
        self.assertEqual(len(set(ids)), 105)
        self.assertEqual(ids, sorted(ids, reverse=True))
        boundary = encode_cursor({'created_at': '2026-01-01T00:00:00+00:00',
                                  'id': 'ffffffff-ffff-ffff-ffff-ffffffffffff'})
        status, orbit = self.call('/v1/orders?' + urlencode({'cursor': boundary}), token='ci-orbit')
        self.assertEqual(status, 200)
        self.assertEqual(len(orbit['orders']), 4)
        self.assertTrue(all(row['external_id'].startswith('page-orbit-') for row in orbit['orders']))
        self.assertFalse(set(ids) & {row['id'] for row in orbit['orders']})

    def test_pagination_index_migration_is_repeatable_and_preserves_orders(self):
        relay_store.create_order('acme', 'index-migration-fixture')
        with relay_store._connect() as conn:
            conn.execute('DROP INDEX IF EXISTS orders_tenant_created_id_idx')
        try:
            migration = Path('db/migrations/002_orders_pagination_index.sql').read_text()
            for _ in range(2):
                with relay_store._connect() as conn:
                    conn.execute(migration)
            with relay_store._connect() as conn:
                index = conn.execute("SELECT to_regclass('orders_tenant_created_id_idx') AS name").fetchone()
                count = conn.execute("SELECT count(*) AS n FROM orders WHERE external_id=%s",
                                     ('index-migration-fixture',)).fetchone()
            self.assertIsNotNone(index['name'])
            self.assertEqual(count['n'], 1)
        finally:
            with relay_store._connect() as conn:
                conn.execute('CREATE INDEX IF NOT EXISTS orders_tenant_created_id_idx ON orders (tenant_id, created_at DESC, id DESC)')



