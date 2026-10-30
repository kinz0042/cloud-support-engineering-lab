# INC-023: Partner redirects a signed webhook

**Scenario:** Synthetic order integration. **Suggested severity:** SEV-3 for one affected integration; escalate if evidence shows broader impact or sensitive data exposure. **Learner investigation:** pending.

## Customer complaint

“Orders are accepted, but our integration has stopped receiving notifications after an endpoint change.”

## Symptoms and environment

The RelayDesk API stores an order and queues delivery. A local mock endpoint returns a redirect rather than a success status. The worker records the redirect status as a failed attempt, and retries according to its normal policy. The lab uses synthetic credentials and an internal HTTP destination; it is not an actual third-party integration.

## Reproduce and gather evidence

From the repository root, run the local HTTP tests:

```sh
python -m unittest discover -s tests -p "test_worker*.py" -v
```

The destination test creates two loopback HTTP servers. The configured server returns 301, 302, 303, 307 and 308, each pointing to the second server. The worker reports failure for each response; the second server receives no request. A separate subprocess supplies proxy environment variables and verifies that the request still goes directly to the configured loopback service. A normal 202 response succeeds. Retry tests cover rate-limit values, invalid headers and response cleanup. These tests do not run PostgreSQL or prove a live partner received anything.

For a Compose investigation, correlate UTC time, delivery ID and attempt number from `docker compose logs --tail=100 worker` with the delivery record:

```sh
docker compose exec db psql -U lab -d relaydesk -c "SELECT id,state,attempts,max_attempts,last_error,next_attempt_at FROM deliveries ORDER BY id DESC LIMIT 10;"
```

Inspect endpoint configuration and the recipient's sanitized access logs. Do not paste URL credentials, signatures, secrets or full payloads into tickets. The worker logs a status code, not the `Location` header. A redirect status alone does not prove the destination or that any signed headers were exposed; establish those facts from appropriate evidence.

## Hypotheses and root cause

Consider an endpoint migration, a reverse-proxy redirect, authentication rejection, network failure, receiver outage or an exhausted retry budget. Compare the worker's exact status, endpoint configuration, recipient evidence and retry history. In this controlled reproduction the first endpoint returns a redirect; the worker does not follow it. Earlier worker code used Python's default redirect handling, which can follow redirects and forward request headers. No real exposure is claimed by this test.

## Resolution and validation

Confirm the intended internal partner endpoint and correct the mock configuration rather than blindly following a redirect. Confirm whether the recipient has processed the event before attempting recovery. If the delivery is still pending, allow its scheduled retry after the endpoint is fixed. If it is dead, follow the [single-delivery replay procedure](../../docs/delivery-recovery.md), including recipient review, inspected attempts and audit reason. Verify delivery state and recipient event ID, and repeat the destination tests. A recorded 2xx indicates the receiver returned success; it does not independently prove downstream business processing.

`Retry-After` numeric seconds are capped at 300 for a 429; invalid and HTTP-date values use ordinary backoff. The worker ignores proxy environment settings and does not follow redirects. Monitor repeated redirect failures and keep an agreed, verified endpoint change process. Production integrations need a separately designed allowlist, TLS, egress controls, idempotency and secret rotation; these tests do not supply them.

## Customer-facing response

“We found that the test partner endpoint is returning a redirect instead of accepting the notification. We are verifying the intended endpoint and whether the event was already processed before retrying. We will confirm delivery after the configuration is corrected. Please share the relevant timestamp and delivery identifier, but not signing secrets or the full payload.”

## Internal notes

Record the delivery ID, sanitized status and timestamps, original configured host, recipient review, attempt count, fix and validation. An operator-set replay confirmation is an assertion, not independent proof that a recipient has not processed an event. If real exposure is suspected in another environment, follow that organization's incident process; this local exercise does not establish one.
