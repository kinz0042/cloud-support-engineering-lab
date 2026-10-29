# INC-003 — Verification evidence

**Status:** assistant-executed simulation. Learner investigation pending. No real customer was affected.

[GitHub Actions run](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40957008653) ran the full Compose environment, stopped the disposable PostgreSQL service, observed that the API health endpoint remained 200 while readiness returned 503, restarted the database, and checked that a previously created Acme order remained readable. The assertions are in `scripts/compose_smoke.py`.

**Symptom and scope:** The fictional customer report is in [the brief](brief.md). The automated experiment validates behavior of one local tenant and does not measure customer impact or data loss during a real incident.

**Hypotheses:** Wrong credentials, an API process outage and database connectivity failure could all be investigated. In this experiment the database was intentionally stopped, the API's health endpoint remained responsive, and readiness failed. That evidence identifies the injected outage; it does not prove which of those hypotheses would apply to an actual customer.

**Resolution:** Restart the disposable database. The test then observed readiness recover and the pre-existing order remain readable. It did not confirm that every pending delivery recovered, so the delivery queue requires separate inspection.

**Preventive action:** For a real incident, investigate why PostgreSQL stopped, identify affected customers and queued work, check monitoring and capacity, and validate recovery against the actual customer workflow. The optional monitoring profile includes a database readiness alert.

**Example customer update:** “We are investigating order failures and checking database availability. We will provide another update when we have confirmed the cause and impact.”

**Engineering handoff:** Include UTC timestamps, request IDs, endpoint and status, readiness results, database service state, deployment changes, and queue status. Redact connection strings and credentials. No message was sent.
