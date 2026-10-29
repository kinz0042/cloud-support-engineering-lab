# INC-015 — Integration remains stuck after the partner recovers

**Synthetic customer complaint:** "Our provider is back online, but yesterday's accepted order still has no notification. Can you resend it?"

**Environment:** local RelayDesk Compose stack. No real customer data or external endpoint. Severity depends on the affected orders, customers, time window and business impact; do not assign it from one HTTP status alone.

## Reproduce and collect evidence

Start the partner in `reject` mode as in [INC-004](../INC-004/brief.md). Create an order with a new external ID. Record its order ID, request ID and UTC time. Leave rejection enabled until the delivery reaches `dead` after five attempts. Then restore the partner to normal. Inspect the delivery and compare it with a new order that can deliver successfully. Explain why partner recovery alone did not requeue the earlier order.

Use the [recovery runbook](../../docs/delivery-recovery.md) to inspect the specific delivery. Collect its last error, attempt counter, state, stable event ID and partner processing record. Never assume a failed sender attempt means the recipient did nothing. Consider pending backoff, retry exhaustion, a wrong endpoint, an invalid signature and a recipient that already processed the event. State which evidence distinguishes each explanation.

## Resolve and validate

After confirming the recipient state and recovery, replay only the intended dead delivery with the inspected attempt count and an incident reason. Validate that the same event ID reaches the recipient, the delivery becomes delivered, the lifetime attempt count increases and exactly one replay audit record exists. A stale replay should be rejected. If the recipient already processed the event, investigate whether any replay is appropriate rather than treating the command as a mandatory step.

The simulated root cause is retry exhaustion while the partner was rejecting requests. The deliberate replay is a recovery action; investigate the original partner failure separately. Record how you would prevent recurrence through monitoring of dead deliveries and a documented escalation/replay policy. Complete the [incident template](../TEMPLATE.md), including customer response, engineering notes, failed hypotheses, commands, rollback/containment and remaining uncertainty.

## Verification status

Verified in [PostgreSQL integration CI](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40968410297) and the [full Compose workflow](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40968410228). See [verification details](verification.md). The smoke test is `scripts/dead_letter_smoke.py`; a passing replay request alone is not an end-to-end result. Learner investigation remains pending.
