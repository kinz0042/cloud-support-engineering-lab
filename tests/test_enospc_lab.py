import errno
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.enospc_lab import PAYLOAD, fault, recovery, write_once

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "enospc_lab.py"


class NoSpaceLabTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform.startswith("linux") and os.path.exists("/dev/full"), "Linux /dev/full required")
    def test_actual_enospc_is_identified(self):
        status, event = fault()
        self.assertEqual(status, 1)
        self.assertEqual(event["errno"], errno.ENOSPC)
        self.assertEqual(event["reason"], "no_space")

    @unittest.skipUnless(sys.platform.startswith("linux") and os.path.exists("/dev/full"), "Linux /dev/full required")
    def test_non_device_is_rejected_before_writing(self):
        with patch("scripts.enospc_lab.os.fstat", return_value=SimpleNamespace(st_mode=0, st_rdev=0)):
            with patch("scripts.enospc_lab.os.write") as write:
                status, event = fault()
        self.assertEqual(status, 2)
        self.assertEqual(event["event"], "fixture_unavailable")
        write.assert_not_called()

    def test_successful_disposable_write_and_readback(self):
        status, event = recovery()
        self.assertEqual(status, 0)
        self.assertTrue(event["readback_verified"])
        self.assertEqual(event["bytes"], len(PAYLOAD))

    def test_other_io_error_is_not_reported_as_disk_full(self):
        with patch("scripts.enospc_lab.os.write", side_effect=OSError(errno.EACCES, "synthetic")):
            status, event = write_once(0, "test")
        self.assertEqual(status, 1)
        self.assertEqual(event["errno"], errno.EACCES)
        self.assertEqual(event["reason"], "other_io_error")

    def test_short_write_does_not_report_success(self):
        with patch("scripts.enospc_lab.os.write", return_value=1):
            status, event = write_once(0, "test")
        self.assertEqual(status, 1)
        self.assertEqual(event["reason"], "short_write")

    @unittest.skipUnless(sys.platform.startswith("linux") and os.path.exists("/dev/full"), "Linux /dev/full required")
    def test_command_line_failure_and_recovery(self):
        for mode, expected_status, expected_event in (("fault", 1, "write_failed"), ("recovery", 0, "write_succeeded")):
            with self.subTest(mode=mode):
                result = subprocess.run([sys.executable, str(SCRIPT), "--mode", mode],
                                        capture_output=True, text=True, timeout=5, check=False)
                self.assertEqual(result.returncode, expected_status, result.stderr)
                self.assertEqual(json.loads(result.stdout)["event"], expected_event)


if __name__ == "__main__":
    unittest.main()
