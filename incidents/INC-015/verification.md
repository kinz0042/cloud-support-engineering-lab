# Exhausted delivery recovery — verification

Status: assistant-executed simulation, verified on 29 October 2026 at commit `553e84d7008700013c493b6261582fe273223f1a`. No customer incident or independent learner work is claimed.

## Observed checks

The [PostgreSQL workflow](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40968410297) passed all 52 tests. The new database cases covered bounded exhaustion and replay, a stable event ID, rejection of an old worker, tenant and stale-attempt checks, concurrent replay requests, rollback when the audit insert fails, and repeatable migration from the prior schema without removing the existing delivery. Database transition tests use zero retry delays; they do not measure production backoff timing.

The [Compose workflow](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40968410228) passed in full. Its new `Verify exhausted delivery replay and audit` step:

1. Created a synthetic order while the partner returned 503 and waited for five actual worker failures and a dead delivery.
2. Restored the partner and queried its persistent event history to confirm this event had not been recorded.
3. Used the operator CLI to requeue the inspected delivery and verified the increased retry ceiling without resetting its attempt counter.
4. Verified delivery recovery with the same event ID, one recipient record and one replay audit record.
5. Rejected a repeated replay request.

The same run passed base API, database outage/recovery, network diagnostics, partner persistence, webhook 503/429 recovery, SQL and monitoring checks. The [OAuth workflow](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40968410186) also passed with the new schema.

## Interpretation and limits

The injected root cause was partner rejection followed by bounded retry exhaustion. The test establishes that recovery requires an explicit replay once the delivery is dead. It does not establish why an external provider failed, prove recipient-side business effects are exactly-once, or verify the learner's ability to investigate an unfamiliar incident.

The actor label and recipient-review acknowledgement are operator-supplied. The audit is atomic with requeue but is not tamper-proof against privileged database changes. Existing local database volumes must receive the documented additive migration before the updated worker starts. These checks ran in disposable CI environments, not on the learner's laptop or in AWS.
