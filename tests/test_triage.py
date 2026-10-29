"""Triage tests against the real local foundation HTTP server."""
import contextlib
import io
import json
import threading
import unittest
from unittest.mock import patch
from app import server
from scripts import triage


class TriageTests(unittest.TestCase):
    def setUp(self):
        self.store = server.OrderStore()
        self.server = server.make_server(port=0, order_store=self.store)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_healthy_foundation_with_profile_default_credential(self):
        output = io.StringIO()
        with patch.dict(triage.BASES, {"foundation": self.base}), \
             patch("sys.argv", ["triage", "--profile", "foundation"]), \
             contextlib.redirect_stdout(output):
            self.assertEqual(triage.main(), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["orders"]["status"], 200)
        self.assertNotIn(server.DEMO_TOKEN, output.getvalue())

    def test_failed_dependency_produces_readiness_evidence(self):
        self.store.available = False
        health = triage.probe(self.base, "/health")
        ready = triage.probe(self.base, "/ready")
        orders = triage.probe(self.base, "/v1/orders", server.DEMO_TOKEN)
        self.assertEqual((health["status"], ready["status"], orders["status"]), (200, 503, 500))
        self.assertIn("Readiness failed", triage.assess(health, ready, orders))

    def test_bad_credential_reports_401_without_echoing_token(self):
        result = triage.probe(self.base, "/v1/orders", "incorrect-test-token")
        self.assertEqual(result["status"], 401)
        self.assertNotIn("incorrect-test-token", json.dumps(result))
        self.assertTrue(result["request_id"])

    def test_unreachable_endpoint_is_not_a_http_status(self):
        self.server.shutdown()
        self.server.server_close()
        result = triage.probe(self.base, "/health", timeout=0.2)
        self.assertIsNone(result["status"])
        self.assertEqual(result["result"], "connection_failed")


if __name__ == "__main__":
    unittest.main()
