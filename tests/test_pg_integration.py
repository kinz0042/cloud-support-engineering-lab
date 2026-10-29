"""Real PostgreSQL contract, enabled only when DATABASE_URL is supplied."""
import os
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import json

from app.relay_api import make_server
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
        partner = make_partner(0, "ci-secret", "normal")
        worker = threading.Thread(target=partner.serve_forever, daemon=True)
        worker.start()
        try:
            endpoint = "http://127.0.0.1:" + str(partner.server_port) + "/webhook"
            success, code, retry = deliver(row, endpoint, "ci-secret")
            self.assertEqual((success, code, retry), (True, "202", None))
            self.assertEqual(relay_store.finish_delivery(row["id"], row["attempts"], True), "delivered")
            self.assertEqual(partner.seen, {"delivery-" + str(row["id"])})
        finally:
            partner.shutdown()
            partner.server_close()
            worker.join()
        self.assertTrue(relay_store.record_callback("ci-event", order_id))
        self.assertFalse(relay_store.record_callback("ci-event", order_id))
