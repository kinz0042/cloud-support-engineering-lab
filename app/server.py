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

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass  # Never log raw request targets or headers.

    def do_GET(self):
        request_id = str(uuid.uuid4())
        path = urlsplit(self.path).path
        route = path if path in ("/health", "/v1/orders") else "unmatched"
        if path == "/health":
            status, body, reason = 200, {"status": "ok"}, "healthy"
        elif path != "/v1/orders":
            status, body, reason = 404, {"error": "not_found"}, "unknown_route"
        else:
            expected = "Bearer " + self.server.api_token
            supplied = self.headers.get("Authorization", "")
            if not hmac.compare_digest(supplied.encode(), expected.encode()):
                status, body, reason = 401, {"error": "unauthorized"}, "invalid_or_missing_credential"
            else:
                status, body, reason = 200, {"orders": [{"id": "ord_demo_001", "status": "received"}]}, "authorized"
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

def make_server(port=8080, token=None):
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.api_token = token if token is not None else os.environ.get("LAB_API_TOKEN", DEMO_TOKEN)
    if not server.api_token:
        server.server_close()
        raise ValueError("LAB_API_TOKEN must not be empty")
    return server

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    with make_server() as server:
        print("Local lab listening at http://127.0.0.1:8080", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
