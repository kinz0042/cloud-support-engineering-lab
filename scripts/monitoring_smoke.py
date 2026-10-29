"""Verify database outage, queue telemetry, and stopped-worker alert recovery."""
import json
import subprocess
import uuid
from urllib.request import Request, urlopen
from prometheus_probe import query, wait_for

def value_is(expression, expected):
    return any(float(x['value'][1]) == expected for x in query(expression))

def compose(*args):
    return subprocess.check_output(['docker', 'compose', *args], text=True).strip()

wait_for(lambda: value_is('up{job="relaydesk"}', 1), 'Prometheus scrape')
wait_for(lambda: value_is('relaydesk_database_ready', 1), 'database readiness metric')
wait_for(lambda: value_is('relaydesk_delivery_metrics_available', 1), 'queue metrics availability')
subprocess.run(['docker', 'compose', 'stop', 'db'], check=True)
try:
    wait_for(lambda: value_is('relaydesk_delivery_metrics_available', 0), 'unavailable queue metrics')
    wait_for(lambda: not query('relaydesk_deliveries'), 'queue gauges absent during database outage')
    wait_for(lambda: bool(query('ALERTS{alertname="RelayDeskDatabaseUnavailable",alertstate="firing"}')),
             'database alert')
finally:
    subprocess.run(['docker', 'compose', 'start', 'db'], check=True)
wait_for(lambda: value_is('relaydesk_database_ready', 1), 'database recovery')
wait_for(lambda: value_is('relaydesk_delivery_metrics_available', 1), 'queue metrics recovery')
wait_for(lambda: not query('ALERTS{alertname="RelayDeskDatabaseUnavailable",alertstate="firing"}'),
         'database alert clearing')

# Deliberately stop the consumer while the API and database remain healthy.
subprocess.run(['docker', 'compose', 'stop', 'worker'], check=True)
try:
    body = json.dumps({'external_id': 'worker-stopped-ci-' + str(uuid.uuid4())}).encode()
    req = Request('http://127.0.0.1:8081/v1/orders', data=body, method='POST',
                  headers={'Authorization': 'Bearer acme-local-key', 'Content-Type': 'application/json'})
    with urlopen(req, timeout=5) as response:
        assert response.status == 201
        order_id = str(uuid.UUID(json.load(response)['order']['id']))
    wait_for(lambda: bool(query('ALERTS{alertname="RelayDeskDeliveryBacklog",alertstate="firing"}')),
             'stopped-worker backlog alert')
    assert value_is('relaydesk_database_ready', 1)
    assert value_is('relaydesk_delivery_metrics_available', 1)
    with urlopen('http://127.0.0.1:8081/health', timeout=3) as response:
        assert response.status == 200
finally:
    subprocess.run(['docker', 'compose', 'start', 'worker'], check=True)


def order_delivered():
    # The UUID validation above prevents arbitrary SQL in this disposable drill.
    state = compose('exec', '-T', 'db', 'psql', '-U', 'lab', '-d', 'relaydesk', '-tAc',
                    "SELECT state FROM deliveries WHERE order_id='" + order_id + "'")
    return state == 'delivered'


wait_for(order_delivered, 'queued order delivery after worker restart')
wait_for(lambda: value_is('relaydesk_oldest_due_delivery_age_seconds', 0), 'due-work age recovery')
wait_for(lambda: not query('ALERTS{alertname="RelayDeskDeliveryBacklog",alertstate="firing"}'),
         'backlog alert clearing')
print('Database alert, telemetry availability, stopped-worker backlog alert and delivery recovery passed')

