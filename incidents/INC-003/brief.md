# INC-003 — Order API cannot reach PostgreSQL

Customer: "Orders fail even though the API process is running. Is our integration misconfigured?"

Run the Compose stack, create a synthetic order, then run `docker compose stop db`. Compare `/health`, `/ready`, authorized `/v1/orders`, API logs and `docker compose ps`. Record the request IDs and exact database connectivity error only in private internal notes; do not expose credentials or raw DSNs. Restore with `docker compose start db`, wait for healthy, and validate reads/writes plus the unaffected tenant.

Hypotheses to test: authentication failure, API process failure, database connection failure. Explain the evidence that separates them. Create a customer update without an unsupported recovery ETA. Complete [the template](../TEMPLATE.md).

Status: implemented scenario; Docker/PostgreSQL outage and recovery have passed the automated CI smoke test; learner investigation is pending. Never intentionally stop a shared or production database.

## Reproduce and investigate

In a disposable stack, start with `docker compose up -d --build`, then check `curl -i http://127.0.0.1:8081/health` and `curl -i http://127.0.0.1:8081/ready`. Stop only the local lab database with `docker compose stop db`. Repeat both checks, then send an authenticated order-list request using the example in [operations](../../docs/operations.md). Capture response status, time and request ID; compare `docker compose ps` and `docker compose logs --tail=50 api db`.

A healthy process with failed readiness supports a dependency failure; it does not alone prove the exact cause. Test authentication separately and use container status and logs to distinguish the stopped database from a bad credential. Restore using `docker compose start db`; wait for readiness, check an authenticated read and a new synthetic write, and confirm tenant isolation. Record evidence and uncertainties in the incident template.

The [Compose integration check](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40964519832) also exercises the triage command during a stopped-database scenario and after recovery; review the run outcome before treating it as verified.
