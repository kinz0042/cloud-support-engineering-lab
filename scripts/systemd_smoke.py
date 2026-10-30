"""Exercise real systemd failure and recovery on a disposable GitHub runner only."""
import errno
import json
import os
from pathlib import Path
import pwd
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from urllib.error import URLError
from urllib.request import urlopen


if os.environ.get("GITHUB_ACTIONS") != "true" or sys.platform != "linux":
    raise SystemExit("This automation is restricted to a disposable GitHub Actions Linux runner")
if os.geteuid() == 0:
    raise SystemExit("Run the lab as an unprivileged runner user, not root")

SERVICE = Path(__file__).resolve().parents[1] / "linux" / "status_service.py"
user = pwd.getpwuid(os.getuid()).pw_name
suffix = uuid.uuid4().hex[:12]
unit_a = "relaydesk-ci-" + suffix + "-a.service"
unit_b = "relaydesk-ci-" + suffix + "-b.service"


def command(*args, check=True):
    return subprocess.run(["sudo", "-n", *args], capture_output=True, text=True, check=check, timeout=20)


def show(unit, property_name):
    result = command("systemctl", "show", unit, "--property=" + property_name, "--value", check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def wait_for(predicate, description, seconds=20):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except (URLError, TimeoutError, ConnectionError, json.JSONDecodeError):
            pass
        time.sleep(0.25)
    raise RuntimeError("Timed out waiting for " + description)


def journal_events(unit):
    result = command("journalctl", "--unit=" + unit, "--no-pager", "--output=cat", check=False)
    events = []
    for line in result.stdout.splitlines():
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def health(port):
    with urlopen("http://127.0.0.1:" + str(port) + "/health", timeout=2) as response:
        return json.load(response)


def launch(unit, env_path):
    # The unit is transient, uses a generated name, and runs as the CI user.
    return command("systemd-run", "--quiet", "--unit=" + unit, "--service-type=exec",
                   "--property=Restart=no", "--property=NoNewPrivileges=yes", "--property=User=" + user,
                   "--property=EnvironmentFile=" + str(env_path),
                   "/usr/bin/python3", str(SERVICE), check=False)


with tempfile.TemporaryDirectory(prefix="relaydesk-systemd-ci-") as temp:
    env_a, env_b = Path(temp) / "alpha.env", Path(temp) / "bravo.env"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env_a.write_text("RELAY_LAB_INSTANCE=\nRELAY_LAB_PORT=" + str(port) + "\n")
    env_b.write_text("RELAY_LAB_INSTANCE=bravo-demo\nRELAY_LAB_PORT=" + str(port) + "\n")
    try:
        first = launch(unit_a, env_a)
        wait_for(lambda: show(unit_a, "ActiveState") == "failed",
                 "configuration failure (systemd-run exit " + str(first.returncode) + ")")
        assert show(unit_a, "ExecMainStatus") == "2"
        wait_for(lambda: any(e.get("event") == "configuration_error" and
                             e.get("reason") == "missing_instance" for e in journal_events(unit_a)),
                 "configuration error in journal")

        env_a.write_text("RELAY_LAB_INSTANCE=alpha-demo\nRELAY_LAB_PORT=" + str(port) + "\n")
        assert show(unit_a, "ActiveState") == "failed", "Editing config must not silently restart a service"
        command("systemctl", "restart", unit_a)
        wait_for(lambda: show(unit_a, "ActiveState") == "active", "first service activation")
        wait_for(lambda: health(port).get("instance") == "alpha-demo", "first service health")
        pid = int(show(unit_a, "MainPID"))
        assert pid > 0
        effective_uid = subprocess.check_output(['ps', '-o', 'euid=', '-p', str(pid)], text=True).strip()
        assert effective_uid == str(os.geteuid()), 'Synthetic service did not run as the runner user'
        assert show(unit_a, 'NoNewPrivileges') == 'yes'

        second = launch(unit_b, env_b)
        wait_for(lambda: show(unit_b, "ActiveState") == "failed",
                 "port conflict (systemd-run exit " + str(second.returncode) + ")")
        assert show(unit_b, "ExecMainStatus") == "1"
        wait_for(lambda: any(e.get("event") == "listen_failed" and
                             e.get("errno") == errno.EADDRINUSE and e.get("address_in_use")
                             for e in journal_events(unit_b)), "address-in-use journal evidence")
        assert health(port)["instance"] == "alpha-demo"

        command("systemctl", "stop", unit_a)
        command("systemctl", "restart", unit_b)
        wait_for(lambda: show(unit_b, "ActiveState") == "active", "second service activation")
        wait_for(lambda: health(port).get("instance") == "bravo-demo", "second service health")
        print(json.dumps({"configuration_failure_status": 2, "port_conflict_status": 1,
                          "conflict_errno": errno.EADDRINUSE, "recovered_instance": "bravo-demo",
                          "unprivileged_runner_user": os.geteuid() != 0,
                          "no_new_privileges": True}))
    except Exception:
        # The only collected journal records belong to the two synthetic units.
        for unit in (unit_a, unit_b):
            print(json.dumps({"unit": unit, "state": show(unit, "ActiveState"),
                              "events": journal_events(unit)}), file=sys.stderr)
        raise
    finally:
        active_after_cleanup = []
        for unit in (unit_a, unit_b):
            command("systemctl", "stop", unit, check=False)
            if show(unit, "ActiveState") in ("active", "activating", "deactivating"):
                active_after_cleanup.append(unit)
            command("systemctl", "reset-failed", unit, check=False)
        if active_after_cleanup:
            print("Synthetic units still active: " + ", ".join(active_after_cleanup), file=sys.stderr)
            if sys.exc_info()[0] is None:
                raise RuntimeError("Systemd lab cleanup did not stop all units")
