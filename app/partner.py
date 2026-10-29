"""Synthetic partner with signature validation and duplicate detection."""
import hashlib
import hmac
import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG = logging.getLogger("relaydesk.partner")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        if self.path != "/webhook":
            self.send_error(404)
            return
        length = self.headers.get("Content-Length", "")
        if not length.isdigit() or int(length) > 4096 or int(length) < 1:
            self.send_error(400)
            return
        raw = self.rfile.read(int(length))
        expected = hmac.new(self.server.secret.encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(self.headers.get("X-Relay-Signature", ""), expected):
            self.send_error(401)
            return
        try:
            event_id = json.loads(raw)["event_id"]
            if not isinstance(event_id, str) or not event_id:
                raise ValueError()
        except (ValueError, KeyError, TypeError):
            self.send_error(400)
            return
        if self.server.mode == "reject":
            self.send_error(503)
            return
        with self.server.lock:
            duplicate = event_id in self.server.seen
            self.server.seen.add(event_id)
        LOG.info(json.dumps({"event": "partner_received", "event_id": event_id, "duplicate": duplicate}))
        self.send_response(202)
        self.send_header("Content-Length", "0")
        self.end_headers()


def make_server(port=8082, secret=None, mode=None, host="127.0.0.1"):
    secret = secret if secret is not None else os.environ["LAB_WEBHOOK_SECRET"]
    mode = mode if mode is not None else os.environ.get("LAB_PARTNER_MODE", "normal")
    if not secret or mode not in ("normal", "reject"):
        raise ValueError("Invalid partner configuration")
    server = ThreadingHTTPServer((host, port), Handler)
    server.secret, server.mode, server.seen, server.lock = secret, mode, set(), threading.Lock()
    return server


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    with make_server(host="0.0.0.0") as server:
        server.serve_forever()
