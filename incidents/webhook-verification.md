# Webhook failure and recovery — CI verification

**Status:** assistant-executed simulation. Learner investigations remain pending. No customer was affected.

The [Compose CI run](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40958701738) successfully completed the webhook recovery step. The executable test is `scripts/webhook_fault_smoke.py`.

- For [INC-004](INC-004/brief.md), the mock partner was configured to reject webhooks with HTTP 503. The test observed that failure in the delivery record, restored the partner to normal, and verified the delivery reached `delivered`.
- For [INC-012](INC-012/brief.md), the mock partner returned HTTP 429. The test observed that failure in the delivery record, restored the partner to normal, and verified delivery recovered. The partner supplies a numeric Retry-After value; a separate HTTP unit test checks that the worker reads it.

**Hypotheses:** Partner outage, wrong destination, invalid signature and rate limiting can all affect deliveries. This test intentionally configures the partner to return each status; the status observed is evidence of those injected faults, not proof about any real partner.

**Customer update example:** “Your order was accepted, but its notification has not reached the partner. We are investigating the delivery attempts and will update you after checking recovery.”

**Internal handoff:** Include event and delivery IDs, request timestamps, HTTP status, retry attempts, any Retry-After value, recipient behavior, and whether processing may have occurred despite an ambiguous response. Redact tokens and signatures. No customer message was sent.

**Limits:** The test verifies recovery before retry exhaustion, not dead-letter replay, partner side effects, or durable deduplication after partner restart. The mock partner's deduplication is in memory. A real case requires impact, severity, independent evidence, safe remediation, validation and preventive action.
