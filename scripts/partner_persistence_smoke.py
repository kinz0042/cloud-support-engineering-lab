"""Verify mock partner deduplication survives container recreation in disposable CI."""
import subprocess
import time

SEND = """
import hashlib, hmac, json, time
from urllib.request import Request, urlopen
body = json.dumps({'event_id': 'persistence-ci-event'}).encode()
timestamp = str(int(time.time()))
signature = hmac.new(b'local-only-webhook-secret', timestamp.encode()+b'.'+body, hashlib.sha256).hexdigest()
req = Request('http://127.0.0.1:8082/webhook', data=body, method='POST',
              headers={'X-Relay-Timestamp': timestamp, 'X-Relay-Signature': signature})
with urlopen(req, timeout=5) as response:
    assert response.status == 202
"""
COUNT = """
import sqlite3
with sqlite3.connect('/var/lib/relaydesk/partner.sqlite3') as conn:
    print(conn.execute("SELECT count(*) FROM seen_events WHERE event_id=?", ('persistence-ci-event',)).fetchone()[0])
"""

def execute(code):
    return subprocess.check_output(['docker', 'compose', 'exec', '-T', 'partner',
                                    'python', '-c', code], text=True).strip()

execute(SEND)
assert execute(COUNT) == '1'
subprocess.run(['docker', 'compose', 'up', '-d', '--no-deps', '--force-recreate', 'partner'], check=True)
deadline = time.monotonic() + 20
while True:
    try:
        execute(SEND)
        break
    except subprocess.CalledProcessError:
        if time.monotonic() >= deadline:
            raise
        time.sleep(1)
assert execute(COUNT) == '1'
logs = subprocess.check_output(['docker', 'compose', 'logs', '--no-color', 'partner'], text=True)
assert '"event_id": "persistence-ci-event", "duplicate": true' in logs
print('Partner event survives container recreation and is recognized as a duplicate')
