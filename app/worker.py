"""Bounded at-least-once delivery worker for synthetic webhooks."""
import hashlib
import hmac
import json
import logging
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from . import relay_store as store

LOG = logging.getLogger("relaydesk.worker")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


# The fixed local partner is the only intended recipient. Ignore ambient proxy
# configuration and treat redirects as failures rather than forwarding headers.
OPENER = build_opener(ProxyHandler({}), NoRedirect())


def retry_after_seconds(value):
    """Accept only ASCII delta-seconds, capped without unbounded integer parsing."""
    if not value or not value.isascii() or not value.isdigit():
        return None
    normalized = value.lstrip("0") or "0"
    return 300 if len(normalized) > 3 else min(int(normalized), 300)


def deliver(row, endpoint, secret):
    body = json.dumps({"event_id": "delivery-" + str(row["id"]),
                       "order_id": row["order_id"], "tenant_id": row["tenant_id"]},
                      separators=(",", ":")).encode()
    timestamp = str(int(time.time()))
    signature = hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    request = Request(endpoint, data=body, method="POST", headers={
        "Content-Type": "application/json", "X-Relay-Signature": signature,
        "X-Relay-Timestamp": timestamp})
    try:
        with OPENER.open(request, timeout=3) as response:
            return 200 <= response.status < 300, str(response.status), None
    except HTTPError as exc:
        with exc:
            retry = exc.headers.get("Retry-After") if exc.code == 429 else None
            return False, str(exc.code), retry_after_seconds(retry)
    except (URLError, TimeoutError):
        return False, "transport_error", None


def run():
    endpoint = os.environ["LAB_PARTNER_URL"]  # Fixed by operator, never supplied by a customer.
    secret = os.environ["LAB_WEBHOOK_SECRET"]
    if not endpoint.startswith("http://partner:8082/"):
        raise ValueError("Partner endpoint must be the internal mock service")
    while True:
        try:
            row = store.claim_delivery()
            if row is None:
                time.sleep(1)
                continue
            success, code, retry_delay = deliver(row, endpoint, secret)
            state = store.finish_delivery(row["id"], row["attempts"], success,
                                          None if success else code, retry_delay)
            LOG.info(json.dumps({"event": "delivery_attempt", "delivery_id": row["id"],
                                 "attempt": row["attempts"], "state": state, "result": code}))
        except Exception as exc:
            # Database exceptions can embed connection details; log only their class.
            LOG.error(json.dumps({"event": "worker_cycle_failed", "error_type": type(exc).__name__}))
            time.sleep(2)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run()
