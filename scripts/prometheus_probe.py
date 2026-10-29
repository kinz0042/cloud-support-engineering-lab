"""Read the local lab's Prometheus API and wait for bounded conditions."""
import json
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen


def query(expression):
    url = 'http://127.0.0.1:9090/api/v1/query?' + urlencode({'query': expression})
    with urlopen(url, timeout=3) as response:
        return json.load(response)['data']['result']


def wait_for(predicate, description, timeout=100):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except (URLError, TimeoutError, ConnectionError, KeyError, ValueError):
            pass
        time.sleep(2)
    raise SystemExit('Timed out waiting for ' + description)
