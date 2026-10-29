"""Read-only RelayDesk health triage for a local synthetic lab."""
import argparse
import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASES = {"foundation": "http://127.0.0.1:8080", "compose": "http://127.0.0.1:8081"}


def probe(base, path, credential=None, timeout=3):
    headers = {"Authorization": "Bearer " + credential} if credential else {}
    req = Request(base + path, headers=headers)
    started = time.monotonic()
    try:
        with urlopen(req, timeout=timeout) as response:
            status = response.status
            request_id = response.headers.get("X-Request-ID")
    except HTTPError as error:
        status = error.code
        request_id = error.headers.get("X-Request-ID") if error.headers else None
        error.close()
    except (URLError, TimeoutError, OSError):
        return {"path": path, "status": None, "result": "connection_failed"}
    return {"path": path, "status": status, "request_id": request_id,
            "duration_ms": round((time.monotonic() - started) * 1000, 1)}


def assess(health, ready, orders):
    if health.get("status") is None:
        return "API unreachable; check process, port and local networking"
    if health["status"] != 200:
        return "Liveness failed; inspect API process and logs"
    if ready and ready.get("status") != 200:
        return "Readiness failed; investigate dependencies and API logs"
    if orders["status"] == 401:
        return "Authentication rejected; verify the lab credential and request"
    if orders["status"] != 200:
        return "Order request failed; correlate request ID with API logs"
    return "Checks passed; asynchronous delivery still requires separate verification"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=BASES, default="compose")
    args = parser.parse_args()
    base = BASES[args.profile]
    health = probe(base, "/health")
    ready = probe(base, "/ready")
    token = "acme-local-key" if args.profile == "compose" else "lab-demo-token-not-a-secret"
    orders = probe(base, "/v1/orders", token)
    print(json.dumps({"profile": args.profile, "health": health, "readiness": ready,
                      "orders": orders, "assessment": assess(health, ready, orders)}, indent=2))
    # Non-zero indicates an incomplete or failing check, not a confirmed root cause.
    return 0 if (health.get("status") == 200 and
                 (ready is None or ready.get("status") == 200) and orders.get("status") == 200) else 1


if __name__ == "__main__":
    sys.exit(main())
