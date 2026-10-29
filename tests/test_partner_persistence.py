"""Verify durable duplicate detection using real loopback requests and SQLite."""
import os
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from app import partner, worker


class PersistentPartnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "events.sqlite")
        self.server = None

    def start(self):
        self.server = partner.make_server(port=0, secret="secret", mode="normal", store_path=self.path)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return f"http://127.0.0.1:{self.server.server_port}/webhook"

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=2)
            self.server = None

    def tearDown(self):
        self.stop()
        self.tmp.cleanup()

    def test_duplicate_survives_server_restart(self):
        row = {"id": 17, "order_id": "order-17", "tenant_id": "acme"}
        with self.assertLogs("relaydesk.partner", level="INFO") as first:
            self.assertTrue(worker.deliver(row, self.start(), "secret")[0])
        self.assertIn('"duplicate": false', first.output[0])
        self.stop()
        with self.assertLogs("relaydesk.partner", level="INFO") as second:
            self.assertTrue(worker.deliver(row, self.start(), "secret")[0])
        self.assertIn('"duplicate": true', second.output[0])
        with sqlite3.connect(self.path) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM seen_events").fetchone()[0], 1)

    def test_concurrent_delivery_records_only_one_event(self):
        row = {"id": 18, "order_id": "order-18", "tenant_id": "acme"}
        url = self.start()
        with self.assertLogs("relaydesk.partner", level="INFO") as logs:
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(lambda _: worker.deliver(row, url, "secret"), range(4)))
        self.assertTrue(all(result[0] for result in results))
        self.assertEqual(sum('"duplicate": false' in entry for entry in logs.output), 1)
        with sqlite3.connect(self.path) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM seen_events").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
