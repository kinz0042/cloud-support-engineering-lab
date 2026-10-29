"""Verify a disposable Compose stack through real HTTP and PostgreSQL."""
import json
import subprocess
import time
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

base = 'http://127.0.0.1:8081'

def call(path, method='GET', data=None, token=None):
    headers = {'Authorization': 'Bearer ' + token} if token else {}
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

deadline = time.monotonic() + 45
while True:
    state = subprocess.check_output(['docker', 'compose', 'exec', '-T', 'db', 'psql', '-U', 'lab',
        '-d', 'relaydesk', '-tAc', "SELECT state FROM deliveries LIMIT 1"], text=True).strip()
    if state == 'delivered':
        break
    if time.monotonic() >= deadline:
        raise SystemExit('Webhook delivery did not complete; final state: ' + state)
    time.sleep(1)
print('Compose API, tenant isolation, order replay and webhook delivery passed')
