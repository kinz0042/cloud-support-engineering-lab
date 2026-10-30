# INC-017 — Slow order reads while readiness remains healthy

**Synthetic customer complaint:** "Our order-history integration is much slower. Some calls now return a temporary error, but your health checks are green."

**Environment:** disposable RelayDesk Compose stack with Prometheus. Severity depends on the affected operations, customers, duration and business impact. This lab deliberately holds a table lock; it is not a real customer outage.

## Reproduce and collect evidence

Use the [latency runbook](../../docs/api-latency.md) to hold the local `orders` table lock, make an authenticated order-list request and compare it with health/readiness responses. Record expected versus actual behavior, request IDs, UTC timestamps, status and processing duration. Inspect the histogram, HTTP status counters and relevant database waits. Capture your actual results rather than copying assumed timings.

Compare these hypotheses with discriminating tests: authentication failure, network delay, unavailable database, a slow query plan, lock contention and explicit query cancellation. A successful connectivity probe does not rule out a blocked order read. A cancellation response alone does not establish the specific cancellation cause. Correlate the request with the injected lock holder and compare behavior after the transaction is released.

## Resolve and validate

For this controlled fault, release the transaction with `ROLLBACK` in its owning session. Confirm the same read succeeds, the lock holder no longer blocks requests, log durations recover and the latency alert eventually clears with valid recent observations. A single manually reproduced slow request may not meet the alert's minimum-volume guard. State what your checks prove and what remains uncertain.

The simulated cause is a conflicting table lock, with a statement timeout limiting prolonged order reads. The timeout is containment, not the root-cause fix. In a real system, investigate the change or transaction that held the lock, and coordinate its resolution with the responsible engineer. Consider transaction discipline, migration planning, query monitoring and suitable latency alerts as preventive actions.

Complete [the incident template](../TEMPLATE.md), including unsuccessful hypotheses, customer-facing response, internal engineering handoff, commands, rollback/containment and hints used. Explain the difference between application processing time, client-observed latency and asynchronous notification delay.

## Verification status

The [PostgreSQL-backed test suite](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40971064030) and [live Compose latency drill](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40971064055) passed. See [verification details](verification.md). No learner investigation is certified complete.
