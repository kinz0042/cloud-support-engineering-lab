"""Local-only HTTP foundation for the order integration support lab."""
import hmac
import json
import logging
import os
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

LOGGER = logging.getLogger("support_lab")
DEMO_TOKEN = "lab-demo-token-not-a-secret"

class OrderStoreUnavailable(Exception):
    """The synthetic order dependency cannot serve requests."""

class OrderStore:
    def __init__(self, available=True):
        self.available = available

    def list_orders(self):
        if not self.available:
            raise OrderStoreUnavailable()
        return [{"id": "ord_demo_001", "status": "received"}]

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass  # Never log raw request targets or headers.

    def do_GET(self):
        request_id = str(uuid.uuid4())
        path = urlsplit(self.path).path
        route = path if path in ("/health", "/ready", "/v1/orders") else "unmatched"
        if path == "/health":
            status, body, reason = 200, {"status": "ok"}, "healthy"
        elif path == "/ready":
            if self.server.order_store.available:
                status, body, reason = 200, {"status": "ready"}, "dependency_ready"
            else:
                status, body, reason = 503, {"status": "unavailable"}, "order_store_unavailable"
        elif path != "/v1/orders":
            status, body, reason = 404, {"error": "not_found"}, "unknown_route"
        else:
            expected = "Bearer " + self.server.api_token
            supplied = self.headers.get("Authorization", "")
            if not hmac.compare_digest(supplied.encode(), expected.encode()):
                status, body, reason = 401, {"error": "unauthorized"}, "invalid_or_missing_credential"
            else:
                try:
                    orders = self.server.order_store.list_orders()
                except OrderStoreUnavailable:
                    status, body, reason = 500, {"error": "internal_error"}, "order_store_unavailable"
                else:
                    status, body, reason = 200, {"orders": orders}, "authorized"
        data = json.dumps({**body, "request_id": request_id}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Request-ID", request_id)
        if status == 401:
            self.send_header("WWW-Authenticate", 'Bearer realm="orders"')
        self.end_headers()
        self.wfile.write(data)
        LOGGER.info(json.dumps({"event": "request_completed", "request_id": request_id,
                                "route": route, "status": status, "reason": reason}))

def make_server(port=8080, token=None, order_store=None):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.api_token = token if token is not None else os.environ.get("LAB_API_TOKEN", DEMO_TOKEN)
    if not server.api_token:
        server.server_close()
        raise ValueError("LAB_API_TOKEN must not be empty")
    if order_store is None:
        mode = os.environ.get("LAB_ORDER_STORE_MODE", "available")
        if mode not in ("available", "unavailable"):
            server.server_close()
            raise ValueError("LAB_ORDER_STORE_MODE must be available or unavailable")
        order_store = OrderStore(available=mode == "available")
    server.order_store = order_store
    return server

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    with make_server() as server:
        print("Local lab listening at http://127.0.0.1:8080", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
