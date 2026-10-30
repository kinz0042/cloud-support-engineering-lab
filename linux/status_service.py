"""Small loopback-only service for the optional Linux systemd lab."""
import errno
import json
import os
import re
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def emit(event, **fields):
    print(json.dumps({"event": event, **fields}, separators=(",", ":")), flush=True)


def configuration(env):
    """Return validated synthetic settings or a non-sensitive error code."""
    instance = env.get("RELAY_LAB_INSTANCE", "")
    port = env.get("RELAY_LAB_PORT", "")
    if not instance:
        return None, "missing_instance"
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", instance):
        return None, "invalid_instance"
    if not port:
        return None, "missing_port"
    if not port.isascii() or not port.isdigit() or len(port) > 5 or not 1024 <= int(port) <= 65535:
        return None, "invalid_port"
    return (instance, int(port)), None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        if self.path == "/health":
            status, payload = 200, {"status": "ok", "instance": self.server.instance}
        else:
            status, payload = 404, {"error": "not_found"}
        body = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    settings, error = configuration(os.environ)
    if error:
        emit("configuration_error", reason=error)
        return 2
    instance, port = settings
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError as exc:
        # Winsock reports WSAEADDRINUSE as 10048; Linux uses EADDRINUSE.
        occupied = exc.errno in (errno.EADDRINUSE, 10048) or getattr(exc, "winerror", None) == 10048
        emit("listen_failed", errno=exc.errno, address_in_use=occupied)
        return 1
    server.instance = instance
    stopping = threading.Event()

    def stop(signum, _frame):
        if not stopping.is_set():
            stopping.set()
            emit("shutdown_requested", signal=signum)
            # shutdown() must run on a different thread from serve_forever().
            threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        emit("service_ready", instance=instance, port=port)
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()
        emit("service_stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
