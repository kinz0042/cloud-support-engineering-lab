"""RelayDesk: local-only synthetic B2B integration API."""
import hashlib
import hmac
import json
import logging
import os
import uuid
import threading
import time
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from . import relay_store as store
from .request_metrics import RequestDurations
from .pagination import encode_cursor, parse_page_query

LOG = logging.getLogger("relaydesk")
MAX_BODY = 4096


def tenant_for(header, keys):
    if not header.startswith("Bearer "):
        return None
    supplied = hashlib.sha256(header[7:].encode()).digest()
    for tenant, key in keys.items():
        if hmac.compare_digest(supplied, hashlib.sha256(key.encode()).digest()):
            return tenant
    return None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def reply(self, status, body, request_id, route, reason):
        data = json.dumps({**body, "request_id": request_id}, separators=(",", ":")).encode()
        duration = max(0.0, self.server.clock() - self.started_at)
        with self.server.metrics_lock:
            self.server.requests[(route, status)] += 1
            self.server.request_durations.observe(route, duration)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Request-ID", request_id)
        if status == 401:
            self.send_header("WWW-Authenticate", 'Bearer realm="relaydesk"')
        self.end_headers()
        LOG.info(json.dumps({"event": "request_completed", "request_id": request_id,
                             "route": route, "status": status, "reason": reason,
                             "duration_ms": round(duration * 1000, 3)}))
        self.wfile.write(data)

    def body_json(self):
        length = self.headers.get("Content-Length", "")
        if not length.isdigit() or int(length) < 1 or int(length) > MAX_BODY:
            raise ValueError("invalid body length")
        raw = self.rfile.read(int(length))
        return raw, json.loads(raw)

    def handle_request(self):
        self.started_at = self.server.clock()
        request_id = str(uuid.uuid4())
        try:
            target = urlsplit(self.path)
        except ValueError:
            return self.reply(400, {"error": "invalid_request"}, request_id, "unmatched", "invalid_target")
        path = target.path
        route = path if path in ("/health", "/ready", "/metrics", "/v1/orders", "/v1/callbacks") else "unmatched"
        if self.command == "GET" and path == "/metrics":
            with self.server.metrics_lock:
                lines = [f'relaydesk_requests_total{{route="{r}",status="{s}"}} {n}'
                         for (r, s), n in sorted(self.server.requests.items())]
                lines.extend(self.server.request_durations.render())
            database_ready = 1 if self.server.store.ready() else 0
            queue_available = 0
            queue_lines = []
            if database_ready:
                try:
                    snapshot = self.server.store.delivery_metrics()
                    queue_lines = [f'relaydesk_deliveries{{state="{state}"}} {snapshot["counts"][state]}'
                                   for state in ("pending", "leased", "delivered", "dead")]
                    queue_lines.append('relaydesk_oldest_due_delivery_age_seconds ' +
                                       str(snapshot["oldest_due_seconds"]))
                    queue_available = 1
                except Exception:
                    # Missing telemetry is not a healthy empty queue. Avoid logging
                    # database exceptions that might disclose connection credentials.
                    pass
            data = ("# TYPE relaydesk_requests_total counter\n" + "\n".join(lines) +
                    "\n# TYPE relaydesk_database_ready gauge\n" +
                    f"relaydesk_database_ready {database_ready}\n" +
                    "# TYPE relaydesk_delivery_metrics_available gauge\n" +
                    f"relaydesk_delivery_metrics_available {queue_available}\n" +
                    "# TYPE relaydesk_deliveries gauge\n" +
                    "# TYPE relaydesk_oldest_due_delivery_age_seconds gauge\n" +
                    "\n".join(queue_lines) + "\n").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return self.wfile.write(data)
        if self.command == "GET" and path == "/health":
            return self.reply(200, {"status": "ok"}, request_id, route, "alive")
        if self.command == "GET" and path == "/ready":
            available = self.server.store.ready()
            return self.reply(200 if available else 503,
                              {"status": "ready" if available else "unavailable"},
                              request_id, route, "database_ready" if available else "database_unavailable")
        if path == "/v1/callbacks" and self.command == "POST":
            try:
                raw, body = self.body_json()
                timestamp = self.headers.get("X-Relay-Timestamp", "")
                if not timestamp.isascii() or not timestamp.isdigit() or len(timestamp) > 12 or abs(time.time() - int(timestamp)) > 300:
                    return self.reply(401, {"error": "invalid_signature"}, request_id, route, "stale_callback")
                digest = hmac.new(self.server.webhook_secret.encode(), timestamp.encode() + b"." + raw,
                                  hashlib.sha256).hexdigest()
                signature = self.headers.get("X-Relay-Signature", "")
                if not hmac.compare_digest(signature.encode(), digest.encode()):
                    return self.reply(401, {"error": "invalid_signature"}, request_id, route, "bad_signature")
                event_id, order_id = body["event_id"], body["order_id"]
                if not isinstance(event_id, str) or not 1 <= len(event_id) <= 100:
                    raise ValueError("bad event id")
                order_id = str(uuid.UUID(order_id))
            except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                return self.reply(400, {"error": "invalid_request"}, request_id, route, "bad_body")
            try:
                fresh = self.server.store.record_callback(event_id, order_id)
            except store.CallbackConflict:
                return self.reply(409, {"error": "event_id_conflict"}, request_id, route, "callback_conflict")
            except store.UnknownOrder:
                return self.reply(404, {"error": "order_not_found"}, request_id, route, "unknown_order")
            except Exception:
                return self.reply(503, {"error": "dependency_unavailable"}, request_id, route, "database_unavailable")
            return self.reply(202, {"accepted": True, "duplicate": not fresh}, request_id, route,
                              "callback_accepted" if fresh else "duplicate_callback")
        if path != "/v1/orders" or self.command not in ("GET", "POST"):
            return self.reply(404, {"error": "not_found"}, request_id, route, "unknown_route")
        tenant = tenant_for(self.headers.get("Authorization", ""), self.server.tenant_keys)
        if tenant is None:
            return self.reply(401, {"error": "unauthorized"}, request_id, route, "invalid_credential")
        if self.command == "GET":
            try:
                limit, cursor = parse_page_query(target.query)
            except ValueError:
                return self.reply(400, {"error": "invalid_pagination"}, request_id, route, "invalid_pagination")
        if self.command == "POST":
            try:
                _, body = self.body_json()
                external_id = body["external_id"]
                if not isinstance(external_id, str) or not 1 <= len(external_id) <= 100:
                    raise ValueError("bad external id")
            except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                return self.reply(400, {"error": "invalid_request"}, request_id, route, "bad_body")
        try:
            if self.command == "GET":
                result, created = self.server.store.list_orders(tenant, limit, cursor), False
            else:
                result, created = self.server.store.create_order(tenant, external_id)
        except store.StoreQueryCanceled:
            return self.reply(503, {"error": "dependency_query_canceled"}, request_id, route,
                              "database_query_canceled")
        except Exception:
            return self.reply(503, {"error": "dependency_unavailable"}, request_id, route, "database_unavailable")
        if self.command == "GET":
            page = result[:limit]
            next_cursor = encode_cursor(page[-1]) if len(result) > limit else None
            return self.reply(200, {"orders": page, "next_cursor": next_cursor}, request_id, route, "listed")
        return self.reply(201 if created else 200, {"order": result, "created": created},
                          request_id, route, "created" if created else "idempotent_replay")

    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request()


def make_server(port=8081, backend=None, keys=None, secret=None):
    keys = keys if keys is not None else json.loads(os.environ.get("LAB_TENANT_KEYS", "{}"))
    secret = secret if secret is not None else os.environ.get("LAB_WEBHOOK_SECRET", "")
    if not isinstance(keys, dict) or not keys or any(not isinstance(v, str) or not v for v in keys.values()):
        raise ValueError("LAB_TENANT_KEYS requires nonempty tenant keys")
    if len(set(keys.values())) != len(keys):
        raise ValueError("Tenant keys must be unique")
    if not secret:
        raise ValueError("LAB_WEBHOOK_SECRET is required")
    server = ThreadingHTTPServer(("127.0.0.1" if backend is not None else "0.0.0.0", port), Handler)
    server.store = backend if backend is not None else store
    server.tenant_keys = keys
    server.webhook_secret = secret
    server.metrics_lock = threading.Lock()
    server.requests = Counter()
    server.clock = time.perf_counter
    server.request_durations = RequestDurations()
    return server


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    with make_server() as server:
        server.serve_forever()


