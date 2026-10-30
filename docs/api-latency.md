# API latency and PostgreSQL lock investigation

The Docker API records a classic request-duration histogram and includes `duration_ms` in its structured JSON response logs. It uses a monotonic clock, so changing the system wall clock does not produce negative durations.

## What the measurement means

The timer starts when the application handler begins routing a GET or POST request and ends when its JSON response has been constructed. It includes authentication, request-body parsing and backend work. It excludes DNS, connection setup, TLS, waiting outside the handler, response transfer and asynchronous webhook delivery. A client can therefore see a different total duration. The metrics endpoint itself is excluded to avoid measuring its own scrapes.

Histogram buckets are cumulative, with boundaries at 10, 50, 100, 250 and 500 milliseconds, then 1, 2.5 and 5 seconds, plus an infinite bucket. The only label is a bounded route name; unknown request paths share `unmatched`. Headers, query strings, customer identifiers and tokens never become metric labels. The histogram and request counters reset when the API process restarts. `duration_ms` is rounded for readability; the histogram sum retains the observed duration.

Useful Prometheus queries:

```promql
sum(rate(relaydesk_request_duration_seconds_sum{route="/v1/orders"}[1m]))
/
sum(rate(relaydesk_request_duration_seconds_count{route="/v1/orders"}[1m]))
```

This gives mean processing time in seconds over the window. To inspect the fraction exceeding 500ms:

```promql
1 - (
  sum(rate(relaydesk_request_duration_seconds_bucket{route="/v1/orders",le="0.5"}[1m]))
  /
  sum(rate(relaydesk_request_duration_seconds_count{route="/v1/orders"}[1m]))
)
```

No traffic can produce an undefined ratio; it is not evidence of a slow API. `RelayDeskOrderLatency` requires more than half of recent order requests above 500ms, at least five observed requests over its one-minute window, and a further fifteen-second hold. These are lab thresholds, not a production SLO. Failed responses are included; compare HTTP status counters and logs. Rolling-window alerts need recent healthy traffic or enough time for old observations to leave the window before clearing.

## Read-query cancellation

Order listing runs in a read-only PostgreSQL transaction with a two-second statement timeout. Connection setup has a separate timeout; this is not an exact two-second end-to-end HTTP deadline. This guard applies to the order-list read, not every database operation in the application.

A PostgreSQL query cancellation returns HTTP 503 with `dependency_query_canceled`, a request ID, and log reason `database_query_canceled`. Cancellation may come from a statement timeout or an explicit operator cancellation; correlate it with database evidence before naming the cause. Internal SQL and connection details are not returned in the HTTP response. Do not increase timeouts as an automatic fix for lock contention.

## Controlled lock reproduction

Use only a disposable local lab. In one terminal, open `docker compose exec db psql -U lab -d relaydesk` and run:

```sql
BEGIN;
SET LOCAL application_name = 'latency-manual-lock';
SET LOCAL idle_in_transaction_session_timeout = '60s';
LOCK TABLE orders IN ACCESS EXCLUSIVE MODE;
```

Keep that terminal available to release the transaction. PostgreSQL terminates the idle lab transaction after the configured limit, but explicitly clean it up when finished. While it is open, make an authenticated order-list request from another terminal:

```sh
curl -i http://127.0.0.1:8081/v1/orders -H 'Authorization: Bearer acme-local-key'
```

PowerShell users can use `curl.exe`. Compare `/health` and `/ready`: process liveness and a successful `SELECT 1` do not establish that the order table is available promptly. Record the response status, request ID, UTC time and correlated processing duration.

Inspect locks and waiters from another `psql` session:

```sql
SELECT a.pid, a.application_name, a.state, a.wait_event_type, a.wait_event,
       pg_blocking_pids(a.pid) AS blockers
FROM pg_stat_activity AS a
WHERE a.datname = current_database();

SELECT pid, mode, granted
FROM pg_locks
WHERE relation = 'orders'::regclass;
```

A waiting request is visible only while it is waiting. The injected transaction's granted lock remains visible until release. These queries omit SQL text, which can contain sensitive values in real systems. An ordinary row lock does not necessarily block a plain SELECT; this scenario deliberately uses a conflicting table lock.

Return to the first terminal and run `ROLLBACK;`. Repeat the same order read and validate recovery. Preserve evidence before and after releasing the lock. Explain why adding an index or restarting an unrelated service would not resolve the held transaction itself.

## Automated verification

`scripts/latency_smoke.py` runs a separate disposable experiment after the other Compose checks. It recreates only the API to reset application counters, records an initial scrape, briefly holds actual PostgreSQL table locks, sends concurrent reads, and captures lock-wait evidence. It then checks the latency alert, verifies the injected lock holders have exited, sends healthy reads and checks alert clearing. The histogram also has deterministic bucket and log-correlation tests. See the [CI verification](../incidents/INC-017/verification.md) for what was actually tested.

The experiment creates synthetic traffic and may produce both slow successful reads and bounded query cancellations. It is not a capacity benchmark, distributed trace, external load test or proof of customer latency. No paid infrastructure is used.

References: [Prometheus histogram semantics](https://prometheus.io/docs/practices/histograms/), [PostgreSQL 17 table locks](https://www.postgresql.org/docs/17/explicit-locking.html), and [PostgreSQL statement-timeout settings](https://www.postgresql.org/docs/current/runtime-config-client.html).
