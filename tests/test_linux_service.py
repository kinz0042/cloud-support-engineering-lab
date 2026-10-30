"""Verify the Linux lab process over a real local socket without systemd."""
import json
import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

SERVICE = Path(__file__).resolve().parents[1] / "linux" / "status_service.py"


def environment(**settings):
    env = dict(os.environ)
    env.pop("RELAY_LAB_INSTANCE", None)
    env.pop("RELAY_LAB_PORT", None)
    env.update(settings)
    env["UNRELATED_PRIVATE_VALUE"] = "do-not-print-this-secret"
    return env


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class LinuxServiceTests(unittest.TestCase):
    def test_missing_or_invalid_configuration_exits_without_echoing_values(self):
        for settings, reason in [({}, "missing_instance"),
                                 ({"RELAY_LAB_INSTANCE": "demo"}, "missing_port"),
                                 ({"RELAY_LAB_INSTANCE": "bad value", "RELAY_LAB_PORT": "12345"}, "invalid_instance"),
                                 ({"RELAY_LAB_INSTANCE": "demo", "RELAY_LAB_PORT": "not-a-port"}, "invalid_port")]:
            with self.subTest(reason=reason):
                result = subprocess.run([sys.executable, str(SERVICE)], env=environment(**settings),
                                        capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(json.loads(result.stdout), {"event": "configuration_error", "reason": reason})
                self.assertNotIn("do-not-print-this-secret", result.stdout + result.stderr)
                self.assertNotIn("bad value", result.stdout + result.stderr)

    def test_conflicting_listener_is_reported_without_printing_environment(self):
        with socket.socket() as incumbent:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                incumbent.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            incumbent.bind(("127.0.0.1", 0))
            incumbent.listen()
            port = incumbent.getsockname()[1]
            result = subprocess.run([sys.executable, str(SERVICE)],
                                    env=environment(RELAY_LAB_INSTANCE="demo", RELAY_LAB_PORT=str(port)),
                                    capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 1)
        event = json.loads(result.stdout)
        self.assertEqual(event["event"], "listen_failed")
        self.assertTrue(event["address_in_use"])
        self.assertNotIn("do-not-print-this-secret", result.stdout + result.stderr)

    def test_healthy_service_and_graceful_termination(self):
        port = free_port()
        proc = subprocess.Popen([sys.executable, str(SERVICE)],
                                env=environment(RELAY_LAB_INSTANCE="alpha-demo", RELAY_LAB_PORT=str(port)),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 5
            while True:
                try:
                    with urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as response:
                        self.assertEqual(json.load(response), {"status": "ok", "instance": "alpha-demo"})
                    break
                except (URLError, TimeoutError):
                    if time.monotonic() >= deadline or proc.poll() is not None:
                        self.fail("Service did not become healthy")
                    time.sleep(0.1)
            with self.assertRaises(HTTPError) as error:
                urlopen(f"http://127.0.0.1:{port}/unknown?token=private", timeout=1)
            self.assertEqual(error.exception.code, 404)
        finally:
            proc.terminate()
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                self.fail("Service did not stop within five seconds")
        events = [json.loads(line) for line in stdout.splitlines()]
        self.assertTrue(any(e["event"] == "service_ready" for e in events))
        if os.name != "nt":
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(events[-1]["event"], "service_stopped")
        self.assertNotIn("private", stdout + stderr)
        self.assertNotIn("do-not-print-this-secret", stdout + stderr)


if __name__ == "__main__":
    unittest.main()
