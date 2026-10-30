# RelayDesk API reference

Base URL for the Docker lab: `http://127.0.0.1:8081`. Data and credentials are synthetic. Do not expose the service to the internet.

| Method | Path | Purpose | Expected status |
|---|---|---|---|
| GET | /health | Process liveness | 200 |
| GET | /ready | PostgreSQL connectivity | 200 or 503 |
| GET | /metrics | Prometheus text metrics | 200 |
| GET | /v1/orders | List the authorized tenant's orders | 200, 401, 503 |
| POST | /v1/orders | Create or replay an order by external ID | 201, 200, 400, 401, 503 |
| POST | /v1/callbacks | Receive and deduplicate a signed callback | 202, 400, 401, 404, 409, 503 |

For orders, supply `Authorization: Bearer <tenant-key>`. Acme and Orbit have distinct local demo keys in Compose. A POST body is JSON, for example `{"external_id":"example-1"}`. The same external ID within the same tenant returns the same order with `created: false`; the same external ID in another tenant creates a separate order. An accepted order queues an asynchronous webhook; it does not prove the partner received it.

For callbacks, sign the exact transmitted bytes: HMAC-SHA256 over the Unix timestamp in seconds, a literal dot, and the JSON body. Supply the hex digest in `X-Relay-Signature` and the timestamp in `X-Relay-Timestamp`. Requests outside five minutes are rejected; event IDs are deduplicated. Repeating an event ID for the same order returns `202` with `duplicate: true`; reusing it for a different order returns `409 event_id_conflict`. Deduplication compares the order ID, not the entire payload. `scripts/send_callback.py` demonstrates the format. The Compose mock partner persists duplicate IDs in its own local SQLite volume; deleting that volume removes its history. The in-memory partner used by some tests resets on restart.

JSON responses include a request ID, also in `X-Request-ID`. Record that ID, UTC time, method, route and status when escalating. Never share bearer keys, webhook secrets or full customer payloads. A 503 may indicate an unavailable dependency or a cancelled order-list query. For a cancelled read the error is `dependency_query_canceled`; use the request ID, logs and database evidence before asserting a root cause. See [API latency](api-latency.md).

## Postman

Import [the local collection](../postman/RelayDesk.postman_collection.json) into Postman. It contains synthetic local keys, health/readiness requests, unauthorized controls and two-tenant order requests. The create request can be safely replayed and may return 201 on the first run or 200 subsequently. Tests check expected status and request ID. Do not replace the demo collection's values with real credentials or publish real customer data.

Postman collection import and execution have not been verified in this environment; HTTP behavior is covered by the automated Python and Compose checks.

