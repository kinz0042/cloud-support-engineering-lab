# RelayDesk API reference

Base URL for the Docker lab: `http://127.0.0.1:8081`. Data and credentials are synthetic. Do not expose the service to the internet.

| Method | Path | Purpose | Expected status |
|---|---|---|---|
| GET | /health | Process liveness | 200 |
| GET | /ready | PostgreSQL connectivity | 200 or 503 |
| GET | /metrics | Prometheus text metrics | 200 |
| GET | /v1/orders | List a page of the authorized tenant's orders | 200, 400, 401, 503 |
| POST | /v1/orders | Create or replay an order by external ID | 201, 200, 400, 401, 408, 503 |
| POST | /v1/callbacks | Receive and deduplicate a signed callback | 202, 400, 401, 404, 408, 409, 503 |

For orders, supply `Authorization: Bearer <tenant-key>`. Acme and Orbit have distinct local demo keys in Compose. A POST body is JSON, for example `{"external_id":"example-1"}`. The same external ID within the same tenant returns the same order with `created: false`; the same external ID in another tenant creates a separate order. An accepted order queues an asynchronous webhook; it does not prove the partner received it.

Direct POST requests require one ASCII decimal `Content-Length` between 1 and 4096 bytes. The local server does not decode `Transfer-Encoding`, including chunked uploads; missing, repeated, conflicting, oversized or incomplete framing is rejected with `400 invalid_request`. If the connection is idle while the declared body is being read, the server returns `408 request_timeout` after three seconds. An unauthenticated order request is rejected before its body is read. The timeout is an **idle** timeout, not a total request deadline: a client that continuously sends data can still keep a thread occupied. This local-only server is not a production-grade HTTP edge. See [INC-022](../incidents/INC-022/brief.md).

Order listing returns `orders` and `next_cursor`. The default page contains at most 100 orders; use `?limit=1` through `?limit=100` to choose a smaller page. If `next_cursor` is a string, send it as `cursor` on the next request; `null` means no further page was found. Invalid, repeated or unknown query parameters produce `400 invalid_pagination`. Authentication is checked before pagination parameters. Cursors encode a timestamp and order ID; they are not encrypted, signed or an authorization credential. Every query remains tenant-scoped, including when a caller changes a cursor.

Ordering uses `created_at DESC, id DESC`, so equal timestamps have a stable tie-breaker. Keyset pagination is not a database snapshot: new rows inserted ahead of the current cursor may not appear in the ongoing traversal, and concurrent updates or deletions can alter results. A client needing consistent exports or continuous sync needs an appropriate snapshot or reconciliation strategy. See the [pagination investigation](api-pagination.md).

For callbacks, sign the exact transmitted bytes: HMAC-SHA256 over the Unix timestamp in seconds, a literal dot, and the JSON body. Supply the hex digest in `X-Relay-Signature` and the timestamp in `X-Relay-Timestamp`. Requests outside five minutes are rejected; event IDs are deduplicated. Repeating an event ID for the same order returns `202` with `duplicate: true`; reusing it for a different order returns `409 event_id_conflict`. Deduplication compares the order ID, not the entire payload. `scripts/send_callback.py` demonstrates the format. The Compose mock partner persists duplicate IDs in its own local SQLite volume; deleting that volume removes its history. The in-memory partner used by some tests resets on restart.

JSON responses include a request ID, also in `X-Request-ID`. Record that ID, UTC time, method, route and status when escalating. Never share bearer keys, webhook secrets or full customer payloads. A 503 may indicate an unavailable dependency or a cancelled order-list query. For a cancelled read the error is `dependency_query_canceled`; use the request ID, logs and database evidence before asserting a root cause. See [API latency](api-latency.md).

## Postman

Import [the local collection](../postman/RelayDesk.postman_collection.json) and run it in order. It checks health, readiness, unauthorized requests, a fresh order and its replay, tenant visibility, malformed JSON, a first-page response and request IDs. Each collection run creates one new synthetic order. See the [Postman investigation workflow](postman-workflow.md) for setup, expected results, limitations and CI verification. Desktop Postman import has not been verified here. Do not replace demo values with real credentials or publish real customer data.

