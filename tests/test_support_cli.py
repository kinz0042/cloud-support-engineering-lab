"""CLI operator safeguards and secret-safe dependency errors."""
import contextlib
import io
import json
import unittest
from unittest.mock import patch
from app import support_cli, relay_store


class SupportCLITests(unittest.TestCase):
    def test_inspect_does_not_invoke_replay(self):
        with patch.object(relay_store, "inspect_delivery", return_value={"state": "dead"}) as inspect, \
             patch.object(relay_store, "replay_delivery") as replay, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(support_cli.main(["inspect", "7", "--tenant", "acme"]), 0)
        inspect.assert_called_once_with(7, "acme")
        replay.assert_not_called()

    def test_replay_requires_recipient_review_before_any_database_access(self):
        args = ["replay", "7", "--tenant", "acme", "--expected-attempts", "5",
                "--actor", "operator", "--reason", "INC-015 review completed"]
        with patch.object(relay_store, "replay_delivery") as replay, \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                support_cli.main(args)
        replay.assert_not_called()

    def test_dependency_error_does_not_expose_database_credentials(self):
        output = io.StringIO()
        with patch.object(relay_store, "inspect_delivery", side_effect=RuntimeError("postgresql://private:secret@host")), \
             contextlib.redirect_stdout(output):
            self.assertEqual(support_cli.main(["inspect", "7", "--tenant", "acme"]), 1)
        self.assertNotIn("secret", output.getvalue())
        self.assertEqual(json.loads(output.getvalue())["error"], "operation_failed")

    def test_store_rejects_missing_review_and_invalid_reason_before_connecting(self):
        with patch.object(relay_store, "_connect") as connect:
            with self.assertRaises(ValueError):
                relay_store.replay_delivery(7, "acme", 5, "operator", "INC-015 checked")
            with self.assertRaises(ValueError):
                relay_store.replay_delivery(7, "acme", 5, "operator", "short", True)
        connect.assert_not_called()
