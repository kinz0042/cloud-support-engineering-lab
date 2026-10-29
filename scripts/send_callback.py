"""Send one synthetic signed callback; repeat to verify idempotency."""
import hashlib
import hmac
import json
import os
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

if len(sys.argv) not in (2, 3):
    raise SystemExit("Usage: python scripts/send_callback.py <order-uuid> [event-id]")
body = json.dumps({"order_id": sys.argv[1], "event_id": sys.argv[2] if len(sys.argv) == 3 else "demo-event-1"}).encode()
secret = os.environ.get("LAB_WEBHOOK_SECRET", "local-only-webhook-secret").encode()
signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
request = Request("http://127.0.0.1:8081/v1/callbacks", data=body, method="POST",
                  headers={"Content-Type": "application/json", "X-Relay-Signature": signature})
try:
    response = urlopen(request, timeout=3)
except HTTPError as exc:
    response = exc
with response:
    print(response.status, response.read().decode())
