"""Regression checks for fault-injection cleanup without starting Docker."""
import os
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "webhook_fault_smoke.py"


class FaultSmokeCleanupTests(unittest.TestCase):
    def test_order_failure_restores_partner_and_propagates(self):
        modes = []

        def fake_run(args, *, env, **kwargs):
            modes.append(env["LAB_PARTNER_MODE"])

        with patch("subprocess.run", side_effect=fake_run), \
             patch("urllib.request.urlopen", side_effect=RuntimeError("order failed")):
            with self.assertRaisesRegex(RuntimeError, "order failed"):
                runpy.run_path(str(SCRIPT), run_name="__main__")
        self.assertEqual(modes, ["reject", "normal"])

    def test_partner_setup_failure_still_attempts_restore(self):
        modes = []

        def fake_run(args, *, env, **kwargs):
            modes.append(env["LAB_PARTNER_MODE"])
            if env["LAB_PARTNER_MODE"] == "reject":
                raise RuntimeError("setup failed")

        with patch("subprocess.run", side_effect=fake_run):
            with self.assertRaisesRegex(RuntimeError, "setup failed"):
                runpy.run_path(str(SCRIPT), run_name="__main__")
        self.assertEqual(modes, ["reject", "normal"])


if __name__ == "__main__":
    unittest.main()
