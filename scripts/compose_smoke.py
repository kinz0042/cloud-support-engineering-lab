"""Verify a disposable Compose stack through real HTTP and PostgreSQL."""
import json
import hashlib
import hmac
import subprocess
import time
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

base = 'http://127.0.0.1:8081'

def call(path, method='GET', data=None, token=None, headers=None):
    headers = dict(headers or {})
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = Request(base + path, data=data, method=method, headers=headers)
    with urlopen(req, timeout=3) as response:
        return response.status, json.load(response)

deadline = time.monotonic() + 45
while True:
    try:
        if call('/ready')[0] == 200:
            break
    except (URLError, HTTPError, TimeoutError):
        pass
    if time.monotonic() >= deadline:
        raise SystemExit('API did not become ready within 45 seconds')
    time.sleep(1)

assert call('/health')[0] == 200
body = b'{"external_id":"ci-compose-order"}'
status, result = call('/v1/orders', 'POST', body, 'acme-local-key')
assert status == 201 and result['created']
assert call('/v1/orders', 'POST', body, 'acme-local-key')[0] == 200
assert len(call('/v1/orders', token='acme-local-key')[1]['orders']) == 1
assert len(call('/v1/orders', token='orbit-local-key')[1]['orders']) == 0
try:
    call('/v1/orders', token='wrong-key')
    raise AssertionError('Invalid token unexpectedly accepted')
except HTTPError as error:
    assert error.code == 401

deadline = time.monotonic() + 45
while True:
    state = subprocess.check_output(['docker', 'compose', 'exec', '-T', 'db', 'psql', '-U', 'lab',
        '-d', 'relaydesk', '-tAc', "SELECT state FROM deliveries LIMIT 1"], text=True).strip()
    if state == 'delivered':
        break
    if time.monotonic() >= deadline:
        raise SystemExit('Webhook delivery did not complete; final state: ' + state)
    time.sleep(1)
timestamp = str(int(time.time()))
callback = json.dumps({'event_id': 'compose-event', 'order_id': result['order']['id']}).encode()
signature = hmac.new(b'local-only-webhook-secret', timestamp.encode() + b'.' + callback, hashlib.sha256).hexdigest()
headers = {'X-Relay-Signature': signature, 'X-Relay-Timestamp': timestamp}
assert not call('/v1/callbacks', 'POST', callback, headers=headers)[1]['duplicate']
assert call('/v1/callbacks', 'POST', callback, headers=headers)[1]['duplicate']

subprocess.run(['docker', 'compose', 'stop', 'db'], check=True)
try:
    assert call('/health')[0] == 200
    try:
        call('/ready')
        raise AssertionError('Readiness unexpectedly succeeded while database stopped')
    except HTTPError as error:
        assert error.code == 503
finally:
    subprocess.run(['docker', 'compose', 'start', 'db'], check=True)
deadline = time.monotonic() + 45
while True:
    try:
        if call('/ready')[0] == 200:
            break
    except (URLError, HTTPError, TimeoutError):
        pass
    if time.monotonic() >= deadline:
        raise SystemExit('Database did not recover')
    time.sleep(1)
assert len(call('/v1/orders', token='acme-local-key')[1]['orders']) == 1
print('Compose API, tenant isolation, order replay, delivery, callback deduplication and database recovery passed')
