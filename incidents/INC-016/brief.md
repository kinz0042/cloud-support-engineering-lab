# INC-016 — Orders are accepted but notifications stop

**Synthetic customer complaint:** "Orders are accepted and your status checks look healthy, but our integration has stopped receiving notifications."

**Environment:** disposable RelayDesk Compose stack with the observability profile. Treat severity as provisional until you establish affected customers, duration and business impact. This deliberately stopped-worker scenario is a lab fault, not a real outage.

## Reproduce

Start `docker compose --profile observability up -d --build` and confirm `/health` and `/ready` on port 8081 return 200. Stop only the local consumer with `docker compose stop worker`. Create a new synthetic order using [operations](../../docs/operations.md) or the [PowerShell example](../../docs/windows-setup.md). Preserve the order ID, request ID, response status and UTC time.

Inspect `/metrics`, worker/container status and the delivery table. Open Prometheus on `http://127.0.0.1:9090` and compare:

- `relaydesk_database_ready`
- `relaydesk_delivery_metrics_available`
- `relaydesk_deliveries{state="pending"}`
- `relaydesk_oldest_due_delivery_age_seconds`
- `ALERTS{alertname="RelayDeskDeliveryBacklog",alertstate="firing"}`

The oldest due-work age must remain above 30 seconds for a further 30 seconds before the backlog alert fires. Scrape and evaluation intervals add delay. The API and its database readiness probe can remain healthy throughout. A previously leased event may not become eligible until its lease expires.

## Investigate

Distinguish these hypotheses with evidence: the API did not persist the order, the database is inaccessible, the consumer is stopped or failing, the partner is rejecting requests, or the delivery is legitimately waiting for retry backoff. Check `docker compose ps -a`, `docker compose logs --tail=100 worker partner api`, and the order's delivery record. The [inspection CLI](../../docs/delivery-recovery.md) shows state, attempts, next-attempt time and lease expiry. Missing metrics mean unknown state, not zero backlog.

The injected cause is a stopped consumer. In a real case, finding a stopped process is a starting point for investigating its exit reason, configuration, resources and deployment history; do not label every backlog a worker outage.

## Recover and validate

For this controlled fault, restart the lab worker with `docker compose start worker`. Confirm the original delivery becomes delivered, the stable event ID appears in the recipient's record, due-work age returns to zero and the backlog alert clears while telemetry remains available. Record positive, negative and regression checks. Pending work normally resumes without a replay; replaying it through the dead-delivery tool should be rejected.

Document a customer update that separates order acceptance from notification delivery, a timeline, failed hypotheses, evidence, engineering handoff and preventive action in [the template](../TEMPLATE.md). Consider queue monitoring and worker supervision, rather than relying only on API health. No external customer notification is sent by this lab alert.

## Verification status

The automated drill is `scripts/monitoring_smoke.py`; it deliberately stops and restores the worker in disposable CI. Live alert and recovery verification is pending for this change. Learner investigation remains pending.
