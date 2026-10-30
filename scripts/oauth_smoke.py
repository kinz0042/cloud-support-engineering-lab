"""Test the optional Keycloak and JWT gateway profile in disposable CI."""
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

identity = 'http://127.0.0.1:8085/realms/relaydesk/protocol/openid-connect/token'
gateway = 'http://127.0.0.1:8083/v1/orders'


def token(client, secret=None):
    data = urlencode({'grant_type': 'client_credentials', 'client_id': client,
                      'client_secret': secret or client + '-local-secret'}).encode()
    with urlopen(Request(identity, data=data, method='POST'), timeout=5) as response:
        return json.load(response)['access_token']


def order_request(access_token=None, query=''):
    headers = {} if access_token is None else {'Authorization': 'Bearer ' + access_token}
    try:
        response = urlopen(Request(gateway + query, headers=headers), timeout=5)
    except HTTPError as error:
        response = error
    with response:
        return response.status, json.load(response)


deadline = time.monotonic() + 150
while True:
    try:
        acme = token('acme-client')
        break
    except (HTTPError, URLError, TimeoutError, ConnectionError):
        if time.monotonic() >= deadline:
            raise SystemExit('Identity provider did not become ready')
        time.sleep(2)

status, result = order_request(acme)
assert status == 200, (status, result)
assert len(result['orders']) >= 1, 'Expected an Acme fixture order from the previous smoke test'
status, first_page = order_request(acme, '?limit=1')
assert status == 200 and len(first_page['orders']) == 1 and first_page['next_cursor'], 'Expected a second Acme page'
status, second_page = order_request(acme, '?' + urlencode({'limit': 1, 'cursor': first_page['next_cursor']}))
assert status == 200 and len(second_page['orders']) == 1
assert first_page['orders'][0]['id'] != second_page['orders'][0]['id']
assert order_request(acme, '?limit=0')[0] == 400
status, result = order_request(token('orbit-client'))
assert status == 200 and result['orders'] == [], (status, result)
assert order_request()[0] == 401
assert order_request('not-a-jwt')[0] == 401
assert order_request(token('wrong-audience'))[0] == 401
assert order_request(token('unknown-tenant'))[0] == 403
try:
    token('acme-client', 'wrong-secret')
    raise AssertionError('Invalid client secret unexpectedly accepted')
except HTTPError as exc:
    assert exc.code == 401
# The fixture realm deliberately issues 20-second tokens.
time.sleep(23)
assert order_request(acme)[0] == 401, 'Expired JWT was accepted'
print('OAuth client credentials, pagination, tenant isolation, wrong secret/audience, malformed and expired tokens verified')
