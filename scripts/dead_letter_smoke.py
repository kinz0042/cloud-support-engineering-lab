"""Exhaust real webhook retries, review recipient state, then replay one delivery."""
import json
import argparse
import os
import subprocess
import time
import uuid
from urllib.request import Request, urlopen
from prometheus_probe import query, wait_for


def compose(*args):
    return subprocess.check_output(["docker", "compose", *args], text=True).strip()


def partner(mode):
    subprocess.run(["docker", "compose", "up", "-d", "--no-deps", "--force-recreate", "partner"],
                   env=dict(os.environ, LAB_PARTNER_MODE=mode), check=True)
    deadline = time.monotonic() + 20
    while True:
        result = subprocess.run(["docker", "compose", "exec", "-T", "partner", "python", "-c",
                                 "import socket; socket.create_connection(('127.0.0.1',8082),timeout=2).close()"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            return
        if time.monotonic() >= deadline:
            raise RuntimeError("Partner did not start")
        time.sleep(1)


def inspect(delivery_id):
    return json.loads(compose("exec", "-T", "api", "python", "-m", "app.support_cli",
                              "inspect", delivery_id, "--tenant", "acme"))


def wait_state(delivery_id, expected, seconds=75):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = inspect(delivery_id)
        if result["state"] == expected:
            return result
        time.sleep(1)
    raise RuntimeError("Delivery did not reach " + expected)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--observe-alerts', action='store_true', help='verify dead-delivery alert in local Prometheus')
args = parser.parse_args()

try:
    partner("reject")
    body = json.dumps({"external_id": "dead-letter-ci-" + str(uuid.uuid4())}).encode()
    req = Request("http://127.0.0.1:8081/v1/orders", data=body, method="POST",
                  headers={"Authorization": "Bearer acme-local-key", "Content-Type": "application/json"})
    with urlopen(req, timeout=5) as response:
        order_id = str(uuid.UUID(json.load(response)["order"]["id"]))
    delivery_id = compose("exec", "-T", "db", "psql", "-U", "lab", "-d", "relaydesk", "-tAc",
                          "SELECT id FROM deliveries WHERE order_id='" + order_id + "'")
    assert delivery_id.isdigit()
    before = wait_state(delivery_id, "dead")
    assert before["attempts"] == before["max_attempts"] == 5
    assert before["last_error"] == "503"
    partner("normal")
    # The injected rejection occurs before recording; independently confirm that
    # this synthetic recipient has not processed the stable event ID.
    count_code = "import sqlite3,sys; c=sqlite3.connect('/var/lib/relaydesk/partner.sqlite3'); print(c.execute('SELECT count(*) FROM seen_events WHERE event_id=?',(sys.argv[1],)).fetchone()[0])"
    event_id = before["event_id"]
    assert compose("exec", "-T", "partner", "python", "-c", count_code, event_id) == "0"
    if args.observe_alerts:
        wait_for(lambda: any(float(x['value'][1]) >= 1 for x in query('relaydesk_deliveries{state="dead"}')),
                 'dead-delivery gauge')
        wait_for(lambda: bool(query('ALERTS{alertname="RelayDeskDeadDeliveries",alertstate="firing"}')),
                 'dead-delivery alert')
    replay_args = ["exec", "-T", "api", "python", "-m", "app.support_cli", "replay", delivery_id,
                   "--tenant", "acme", "--expected-attempts", "5", "--actor", "ci-operator",
                   "--reason", "INC-015 synthetic recipient recovered and processing checked", "--recipient-checked"]
    replayed = json.loads(compose(*replay_args))
    assert replayed["attempts"] == 5 and replayed["max_attempts"] == 10
    after = wait_state(delivery_id, "delivered")
    assert after["event_id"] == event_id and 5 < after["attempts"] <= 10
    assert len(after["replays"]) == 1
    assert compose("exec", "-T", "partner", "python", "-c", count_code, event_id) == "1"
    rejected = subprocess.run(["docker", "compose", *replay_args], capture_output=True, text=True)
    assert rejected.returncode == 2
    assert json.loads(rejected.stdout)["error"] == "replay_rejected"
    if args.observe_alerts:
        wait_for(lambda: any(x['value'][1] == '0' for x in query('relaydesk_deliveries{state="dead"}')),
                 'dead-delivery gauge recovery')
        wait_for(lambda: not query('ALERTS{alertname="RelayDeskDeadDeliveries",alertstate="firing"}'),
                 'dead-delivery alert clearing')
    print("Five failures, recipient review, audited replay, stable event ID and recovery verified")
finally:
    partner("normal")

