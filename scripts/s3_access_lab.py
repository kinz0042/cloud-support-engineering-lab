"""Loopback-only object-access teaching fixture; this is not an AWS emulator."""

import argparse
import json
import logging
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "cloud" / "aws-s3" / "fixtures"
LOG = logging.getLogger("s3_access_lab")

# All objects are invented and exist only in memory, never in a real bucket.
OBJECTS = {
    "allowed/readme.txt": "Synthetic reference object",
    "reports/settlement-demo.json": "Synthetic settlement report",
    "reports/other-demo.json": "Synthetic unrelated report",
    "private/payroll-demo.json": "Synthetic restricted object",
}


def load_policy(phase):
    if phase not in ("broken", "recovered"):
        raise ValueError("phase must be broken or recovered")
    policy = json.loads((FIXTURES / (phase + "-access.json")).read_text(encoding="utf-8"))
    fields = ("allow_list_prefixes", "allow_get_prefixes", "allow_get_exact", "deny_get_prefixes")
    if policy.get("label") != phase or not isinstance(policy.get("principal"), str) or not policy["principal"]:
        raise ValueError("invalid teaching fixture metadata")
    for field in fields:
        value = policy.get(field)
        if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
            raise ValueError("invalid teaching fixture list: " + field)
    return policy


def decide_get(policy, key):
    """Apply only the deliberately narrow toy fixture rules, not AWS IAM."""
    if any(key.startswith(prefix) for prefix in policy["deny_get_prefixes"]):
        return False, "explicit_toy_deny"
    if key in policy["allow_get_exact"] or any(key.startswith(prefix) for prefix in policy["allow_get_prefixes"]):
        return True, "toy_allow"
    return False, "no_toy_allow"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass  # Do not log request headers or raw URLs.

    def reply(self, status, payload, request_id, route, reason):
        data = json.dumps({**payload, "request_id": request_id}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Request-ID", request_id)
        self.end_headers()
        self.wfile.write(data)
        LOG.info(json.dumps({"event": "toy_access_request", "request_id": request_id,
                             "route": route, "status": status, "reason": reason}))

    def do_GET(self):
        request_id = str(uuid.uuid4())
        target = urlsplit(self.path)
        path = target.path
        if path == "/health":
            return self.reply(200, {"status": "ok"}, request_id, "health", "healthy")
        if path not in ("/v1/list", "/v1/get", "/v1/policy"):
            return self.reply(404, {"error": "not_found"}, request_id, "unmatched", "unknown_route")
        if self.headers.get("X-Lab-Principal", "") != self.server.policy["principal"]:
            return self.reply(401, {"error": "unknown_lab_principal"}, request_id, path, "unknown_principal")
        if path == "/v1/policy":
            return self.reply(200, {"toy_policy": self.server.policy}, request_id, path, "policy_inspected")
        params = parse_qs(target.query, keep_blank_values=True)
        expected = "prefix" if path == "/v1/list" else "key"
        if set(params) != {expected} or len(params[expected]) != 1 or not params[expected][0] or len(params[expected][0]) > 512:
            return self.reply(400, {"error": "invalid_request"}, request_id, path, "invalid_parameter")
        value = params[expected][0]
        if path == "/v1/list":
            if value not in self.server.policy["allow_list_prefixes"]:
                return self.reply(403, {"error": "AccessDenied"}, request_id, path, "no_toy_list_allow")
            keys = sorted(key for key in OBJECTS if key.startswith(value))
            return self.reply(200, {"keys": keys}, request_id, path, "toy_list_allowed")
        allowed, reason = decide_get(self.server.policy, value)
        if not allowed:
            return self.reply(403, {"error": "AccessDenied"}, request_id, path, reason)
        if value not in OBJECTS:
            # This is a toy response. Real S3 may return 403 for a missing object.
            return self.reply(404, {"error": "synthetic_object_not_found"}, request_id, path, "toy_missing")
        return self.reply(200, {"value": OBJECTS[value]}, request_id, path, "toy_get_allowed")


def make_server(port=8095, phase="broken"):
    policy = load_policy(phase)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.policy = policy
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("broken", "recovered"), default="broken")
    parser.add_argument("--port", type=int, default=8095)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    with make_server(args.port, args.phase) as server:
        print(f"Synthetic object-access lab: http://127.0.0.1:{server.server_port} ({args.phase})", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
