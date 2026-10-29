"""Local-only OAuth resource server and fixed RelayDesk reverse proxy."""
import json
import logging
import os
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LOG = logging.getLogger('relaydesk.oauth')


class AuthInvalid(Exception):
    pass


class AuthUnavailable(Exception):
    pass


class TokenVerifier:
    def __init__(self, issuer, audience, jwks_url):
        import jwt
        self.jwt = jwt
        self.client = jwt.PyJWKClient(jwks_url, timeout=3)
        self.issuer, self.audience = issuer, audience

    def validate(self, token):
        jwt = self.jwt
        try:
            key = self.client.get_signing_key_from_jwt(token)
            return jwt.decode(token, key.key, algorithms=['RS256'], issuer=self.issuer,
                              audience=self.audience, options={'require': ['exp', 'iat', 'iss', 'aud', 'sub']})
        except jwt.PyJWKClientConnectionError as exc:
            raise AuthUnavailable() from exc
        except jwt.PyJWTError as exc:
            raise AuthInvalid() from exc


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, status, body, request_id, reason):
        payload = json.dumps({'error': body, 'request_id': request_id}).encode()
        LOG.info(json.dumps({'event': 'oauth_request', 'request_id': request_id,
                             'status': status, 'reason': reason}))
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('X-Request-ID', request_id)
        if status == 401:
            self.send_header('WWW-Authenticate', 'Bearer realm="relaydesk-oauth"')
        self.end_headers()
        self.wfile.write(payload)

    def handle_request(self):
        request_id = str(uuid.uuid4())
        if self.path != '/v1/orders' or self.command not in ('GET', 'POST'):
            return self.reply(404, 'not_found', request_id, 'unknown_route')
        auth = self.headers.get('Authorization', '')
        if not auth.startswith('Bearer ') or len(auth) > 10000:
            return self.reply(401, 'unauthorized', request_id, 'missing_token')
        try:
            claims = self.server.verifier.validate(auth[7:])
        except AuthUnavailable:
            return self.reply(503, 'identity_unavailable', request_id, 'jwks_unavailable')
        except AuthInvalid:
            return self.reply(401, 'unauthorized', request_id, 'invalid_token')
        tenant = claims.get('tenant_id')
        if not isinstance(tenant, str) or tenant not in self.server.tenant_keys:
            return self.reply(403, 'forbidden', request_id, 'unmapped_tenant')
        data = None
        if self.command == 'POST':
            length = self.headers.get('Content-Length', '')
            if not length.isascii() or not length.isdigit() or len(length) > 5 or int(length) < 1 or int(length) > 4096:
                return self.reply(400, 'invalid_request', request_id, 'bad_body')
            data = self.rfile.read(int(length))
        req = Request('http://api:8081/v1/orders', method=self.command, data=data,
                      headers={'Authorization': 'Bearer ' + self.server.tenant_keys[tenant],
                               'Content-Type': 'application/json'})
        try:
            response = urlopen(req, timeout=5)
        except HTTPError as exc:
            response = exc
        except (URLError, TimeoutError):
            return self.reply(503, 'upstream_unavailable', request_id, 'upstream_unavailable')
        with response:
            payload = response.read(65537)
            if len(payload) > 65536:
                return self.reply(502, 'upstream_response_too_large', request_id, 'upstream_error')
            status, upstream_id = response.status, response.headers.get('X-Request-ID', '')
        LOG.info(json.dumps({'event': 'oauth_request', 'request_id': request_id, 'status': status,
                             'reason': 'forwarded', 'upstream_request_id': upstream_id}))
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('X-Request-ID', request_id)
        if upstream_id:
            self.send_header('X-Upstream-Request-ID', upstream_id)
        self.end_headers()
        self.wfile.write(payload)

    do_GET = handle_request
    do_POST = handle_request


def make_server(host='0.0.0.0', port=8083):
    keys = json.loads(os.environ['LAB_TENANT_KEYS'])
    if not isinstance(keys, dict) or not keys or any(not isinstance(k, str) or not isinstance(v, str) or not v for k, v in keys.items()):
        raise ValueError('Invalid demo tenant mapping')
    verifier = TokenVerifier(os.environ['OIDC_ISSUER'], os.environ['OIDC_AUDIENCE'], os.environ['OIDC_JWKS_URL'])
    server = ThreadingHTTPServer((host, port), Handler)
    server.tenant_keys, server.verifier = keys, verifier
    return server


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    with make_server() as server:
        server.serve_forever()
