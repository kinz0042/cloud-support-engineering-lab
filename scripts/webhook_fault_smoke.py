"""Exercise partner 503/429 failures and recovery in a disposable Compose stack."""
import json
import os
import subprocess
import time
import uuid
from urllib.request import Request, urlopen

def command(*args, env=None):
    return subprocess.check_output(['docker', 'compose', *args], env=env, text=True)

def partner(mode):
    env = dict(os.environ, LAB_PARTNER_MODE=mode)
    subprocess.run(['docker', 'compose', 'up', '-d', '--no-deps', '--force-recreate', 'partner'],
                   env=env, check=True, stdout=subprocess.DEVNULL)

def create_order(external_id):
    request = Request('http://127.0.0.1:8081/v1/orders',
                      data=json.dumps({'external_id': external_id}).encode(), method='POST',
                      headers={'Authorization': 'Bearer acme-local-key', 'Content-Type': 'application/json'})
    with urlopen(request, timeout=5) as response:
        return str(uuid.UUID(json.load(response)['order']['id']))

def state(order_id):
    # order_id was validated as a UUID above and contains no SQL syntax.
    sql = "SELECT state || ':' || coalesce(last_error,'') FROM deliveries WHERE order_id='" + order_id + "'"
    return command('exec', '-T', 'db', 'psql', '-U', 'lab', '-d', 'relaydesk', '-tAc', sql).strip()

def await_state(order_id, predicate, description, seconds=45):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = state(order_id)
        if predicate(result):
            return result
        time.sleep(1)
    raise SystemExit(description + ': ' + state(order_id))

for mode, code in [('reject', '503'), ('rate_limit', '429')]:
    try:
        partner(mode)
        order_id = create_order('ci-' + mode + '-' + str(uuid.uuid4()))
        await_state(order_id, lambda value: value.endswith(':' + code), mode + ' failure not observed')
    finally:
        partner('normal')
    await_state(order_id, lambda value: value == 'delivered:', mode + ' delivery did not recover')
    print(mode + ': observed ' + code + ' and subsequent delivery')
