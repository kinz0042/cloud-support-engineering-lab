# Mock interview review guide

These are reviewer notes for [the mock interview scenarios](mock-interviews.md). They describe expected reasoning, not proof of a learner's performance. Review only after attempting each case.

## 1. OAuth token failure

The visible failure is at token issuance, before an API call using an access token. A healthy endpoint does not establish that this client's credentials or configuration are valid. Another client's success suggests the service is not wholly unavailable, but does not prove the affected client's cause.

Plausible hypotheses include a stale or incorrect secret, wrong client ID or environment, disabled client, or an incorrectly constructed token request. Ask the customer to compare client ID, environment, grant type and rotation timing with their identity-provider configuration; never request the secret itself. Verify with a newly issued token and an authenticated API call, then run a safe missing-token negative control. Explain that the cause remains unconfirmed until evidence distinguishes the alternatives.

A good initial update acknowledges impact, states that token issuance is under investigation and requests nonsecret context. A good handoff includes timestamp, environment, endpoint, status, client identifier if safe, relevant request ID if available, attempted controls and uncertainty.

## 2. Slow API with healthy readiness

The evidence supports a lock wait associated with the identified blocking session and a cancelled order query. It does not establish why that session obtained or retained the lock, the extent of customer impact, or whether unrelated latency sources also exist. Healthy readiness tests connectivity and is not evidence that every query is fast.

Compare `pg_blocking_pids`, wait events, transaction state and query timing against a control after the blocker is removed. Inspect a query plan only when appropriate; a plan alone does not explain this observed wait. In the controlled lab, release the deliberate transaction by rolling back in its owning session. In production, identify the owner and coordinate: do not terminate sessions or roll back someone else's transaction without authorization and impact assessment.

Validate the blocking relationship clears, affected requests complete normally, request timings improve and monitoring recovers according to its window. The statement timeout limits duration; it does not remove the underlying lock. Explain uncertainty about the original transaction and follow up with its owner.

## 3. Webhook replay request

The new order proves only that the recovered path delivered that new event. A dead delivery remains exhausted until explicitly handled. A failed sender attempt does not prove the recipient did not process an event, so check recipient-side history and the stable event ID first.

If the recipient confirms it did not process the event and replay is authorized, inspect the exact dead delivery, use the documented replay mechanism with the observed attempt count and an incident reason, then verify recipient processing, sender state, stable event ID and audit record. If the recipient already processed it, investigate reconciliation and idempotency before any replay. Do not assume replay is automatically safe.

The customer update should say the provider is reachable again while the status of the older notification is being checked. Avoid claiming data loss or successful delivery until supported. The engineering handoff should include the redacted event and delivery identifiers, attempt history, recipient evidence, decision, validation and remaining uncertainty.

## Review rubric

Award 0 for absent, unsafe or unsupported statements; 1 for a partially correct answer; 2 for clear, evidence-backed reasoning in each category. Unsafe changes, exposed secrets or invented results require a failed practice attempt even if the numerical target is reached. Record assistance and retest with different evidence; memorising these examples is not an independent assessment.
