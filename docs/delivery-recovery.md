# Inspecting and recovering an exhausted webhook

The worker initially makes at most five attempts per delivery. Restoring the partner does not automatically requeue a dead delivery. The operator CLI supports an explicit, tenant-scoped replay of one dead delivery after checking what happened at the recipient. This is a local synthetic lab tool, not a production administration service.

## Inspect before acting

Find the delivery ID associated with the customer's order using the query in [operations](operations.md), then replace `DELIVERY_ID` below:

```sh
docker compose exec api python -m app.support_cli inspect DELIVERY_ID --tenant acme
```

Inspection uses a read-only database transaction. It returns the stable event ID, order ID, state, attempt counter, retry ceiling, last error, next-attempt time and replay history. A request for another tenant's delivery returns not found. The tenant option prevents accidental scope mistakes; it is not a separate authorization system. The operator has the database permissions of the API container.

Correlate the order, delivery and event IDs with worker and partner logs. Review the recipient's processing record. An ambiguous timeout can mean the recipient processed the request without the sender seeing the response. A replay may have side effects even when the sender recorded failure. In this lab the partner persists its event IDs; a real recipient needs its own processing evidence.

## Replay one reviewed delivery

After restoring the cause of failure and checking the recipient, use the attempt count from your inspection. This example assumes it was exactly five:

```sh
docker compose exec api python -m app.support_cli replay DELIVERY_ID --tenant acme --expected-attempts 5 --actor lab-operator --reason "INC-015 partner restored and recipient processing reviewed" --recipient-checked
```

The command requeues only a dead delivery whose ID, tenant and attempt count match. It records the supplied operator label, reason, previous attempt count, new retry ceiling and database timestamp in the same transaction as the requeue. It preserves the delivery ID and therefore the webhook event ID. The operator label is self-reported, not an authenticated identity. The audit table is not tamper-proof against a privileged database user. Use synthetic incident notes; do not put credentials or customer payloads in reasons.

The lifetime attempt counter never resets: a replay after five attempts allows at most five additional attempts, with a ceiling of ten. A later failure requires another explicit investigation and replay decision. Keeping attempts monotonic also prevents a worker from an older attempt completing a newer lease. Backoff remains capped at sixty seconds unless a numeric 429 Retry-After supplies a delay capped at five minutes.

Inspect again and verify delivery state, worker logs, recipient processing and the single audit record. A successful replay command proves that a requeue committed, not that delivery succeeded. A duplicate or stale replay request exits with code 2 and does not add an audit record. Dependency failure exits with code 1 without printing connection credentials.

## Existing database upgrade

Fresh volumes receive the schema from `db/init.sql`. Existing lab volumes need the additive migration before the new worker starts. From the repository root, pause the API and worker and start the database:

```sh
docker compose stop api worker
docker compose up -d db
docker compose exec -T db psql -v ON_ERROR_STOP=1 -U lab -d relaydesk < db/migrations/001_delivery_replay.sql
docker compose up -d --build api worker partner
```

PowerShell does not support the same input-redirection syntax. Replace the migration command with:

```powershell
Get-Content -Raw db/migrations/001_delivery_replay.sql | docker compose exec -T db psql -v ON_ERROR_STOP=1 -U lab -d relaydesk
if ($LASTEXITCODE -ne 0) { throw 'Migration failed; inspect the error before restarting the application' }
```

Review migration output before restarting services. The migration is transactional and may be rerun; it adds a column and audit table without deleting orders or deliveries. Take an appropriate backup if the local data matters. Avoid using `down -v` as an upgrade step because it removes both database and partner history. Retain the additive schema if rolling application code back; do not delete audit evidence as a rollback shortcut.

## Validation coverage

PostgreSQL tests cover exhaustion, successful replay, an unchanged event ID, old-worker rejection, concurrent replay requests, tenant/stale-state rejection, bounded additional attempts, atomic rollback on audit failure and migration from the previous schema. The Compose drill waits for five real worker failures, checks recipient history, uses the CLI and verifies delivery recovery. Consult the linked workflow evidence in [INC-015](../incidents/INC-015/brief.md) for the latest verified result; authored tests alone are not proof that they passed.
