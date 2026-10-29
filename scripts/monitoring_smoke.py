"""Verify Prometheus scrapes the live lab and evaluates a database alert."""
import json
import subprocess
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

base = 'http://127.0.0.1:9090'

def query(expression):
    with urlopen(base + '/api/v1/query?' + urlencode({'query': expression}), timeout=3) as response:
        return json.load(response)['data']['result']

def wait_for(predicate, description, timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except (URLError, TimeoutError, KeyError, ValueError):
            pass
        time.sleep(2)
    raise SystemExit('Timed out waiting for ' + description)

wait_for(lambda: any(x['value'][1] == '1' for x in query('up{job="relaydesk"}')), 'Prometheus scrape')
wait_for(lambda: any(x['value'][1] == '1' for x in query('relaydesk_database_ready')), 'database readiness metric')
subprocess.run(['docker', 'compose', 'stop', 'db'], check=True)
try:
    wait_for(lambda: any(x['value'][1] == '1' for x in query('ALERTS{alertname="RelayDeskDatabaseUnavailable",alertstate="firing"}')), 'database alert')
finally:
    subprocess.run(['docker', 'compose', 'start', 'db'], check=True)
wait_for(lambda: any(x['value'][1] == '1' for x in query('relaydesk_database_ready')), 'database recovery')
wait_for(lambda: not query('ALERTS{alertname="RelayDeskDatabaseUnavailable",alertstate="firing"}'), 'alert clearing')
print('Prometheus scrape, database outage alert and recovery passed')
