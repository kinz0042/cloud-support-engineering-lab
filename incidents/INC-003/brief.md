# INC-003 — Order API cannot reach PostgreSQL

Customer: "Orders fail even though the API process is running. Is our integration misconfigured?"

Run the Compose stack, create a synthetic order, then run `docker compose stop db`. Compare `/health`, `/ready`, authorized `/v1/orders`, API logs and `docker compose ps`. Record the request IDs and exact database connectivity error only in private internal notes; do not expose credentials or raw DSNs. Restore with `docker compose start db`, wait for healthy, and validate reads/writes plus the unaffected tenant.

Hypotheses to test: authentication failure, API process failure, database connection failure. Explain the evidence that separates them. Create a customer update without an unsupported recovery ETA. Complete [the template](../TEMPLATE.md).

Status: implemented scenario; Docker/PostgreSQL outage and recovery have passed the automated CI smoke test; learner investigation is pending. Never intentionally stop a shared or production database.
