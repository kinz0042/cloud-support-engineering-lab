"""Measure real lock waits and verify a local order-latency alert and recovery."""
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from prometheus_probe import query, wait_for


def sql(statement):
    return subprocess.check_output(['docker', 'compose', 'exec', '-T', 'db', 'psql',
                                    '-v', 'ON_ERROR_STOP=1', '-U', 'lab', '-d', 'relaydesk',
                                    '-tAc', statement], text=True).strip()


def read_orders():
    request = Request('http://127.0.0.1:8081/v1/orders',
                      headers={'Authorization': 'Bearer acme-local-key'})
    try:
        response = urlopen(request, timeout=5)
    except HTTPError as error:
        response = error
    with response:
        body = json.load(response)
        assert response.status == 200 or (response.status == 503 and
                                          body.get('error') == 'dependency_query_canceled')
        return response.status, body['request_id']


def api_ready():
    with urlopen('http://127.0.0.1:8081/ready', timeout=3) as response:
        return response.status == 200


def value_is(expression, expected):
    return any(float(x['value'][1]) == expected for x in query(expression))


# Isolate this experiment's counters. Database data and partner history remain.
subprocess.run(['docker', 'compose', 'up', '-d', '--no-deps', '--force-recreate', 'api'], check=True)
wait_for(api_ready, 'API restart')
assert read_orders()[0] == 200
wait_for(lambda: value_is('relaydesk_request_duration_seconds_count{route="/v1/orders"}', 1),
         'fresh order histogram scrape')

observed_blocking = False
for burst in range(3):
    holder = subprocess.Popen(['docker', 'compose', 'exec', '-T', 'db', 'psql', '-v', 'ON_ERROR_STOP=1',
                               '-U', 'lab', '-d', 'relaydesk', '-c',
                               "BEGIN; SET LOCAL application_name='latency-ci-lock'; "
                               "SET LOCAL statement_timeout='4s'; "
                               "LOCK TABLE orders IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep(1.8); COMMIT;"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 3
        held = False
        while time.monotonic() < deadline and holder.poll() is None:
            held = sql("SELECT EXISTS(SELECT 1 FROM pg_locks l JOIN pg_stat_activity a ON a.pid=l.pid "
                       "WHERE l.relation='orders'::regclass AND l.mode='AccessExclusiveLock' "
                       "AND l.granted AND a.application_name='latency-ci-lock')") == 't'
            if held:
                break
            time.sleep(0.05)
        assert held, 'Did not observe the injected lock; do not claim a latency reproduction'
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(read_orders) for _ in range(4)]
            waiting = sql("SELECT count(*) FROM pg_stat_activity "
                          "WHERE wait_event_type='Lock' AND cardinality(pg_blocking_pids(pid))>0")
            observed_blocking = observed_blocking or int(waiting) > 0
            outcomes = [future.result() for future in futures]
        _, error = holder.communicate(timeout=8)
        assert holder.returncode == 0, 'Lock-holder transaction failed: ' + error
        print(json.dumps({'burst': burst + 1, 'blocked_sessions_observed': int(waiting),
                          'responses': [{'status': status, 'request_id': rid} for status, rid in outcomes]}))
    finally:
        if holder.poll() is None:
            try:
                holder.communicate(timeout=8)
            except subprocess.TimeoutExpired:
                holder.kill()
                holder.communicate()
                raise

assert observed_blocking, 'No lock wait was observed'
wait_for(lambda: bool(query('ALERTS{alertname="RelayDeskOrderLatency",alertstate="firing"}')),
         'order-latency alert')
assert api_ready()
assert sql("SELECT count(*) FROM pg_stat_activity WHERE application_name='latency-ci-lock'") == '0'

# Validate recovered reads at normal speed, then allow the rolling-window rule
# to reflect that recovery. The lookback does not forget slow requests instantly.
for _ in range(30):
    assert read_orders()[0] == 200
wait_for(lambda: not query('ALERTS{alertname="RelayDeskOrderLatency",alertstate="firing"}'),
         'order-latency alert clearing')
assert read_orders()[0] == 200
print('Observed lock waits, server latency histogram, latency alert and unlocked read recovery passed')
