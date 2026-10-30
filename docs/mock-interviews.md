# Support engineering mock interviews

These are synthetic interview exercises built around RelayDesk's existing incidents. The evidence below is illustrative, not a recording of a real customer or an automated test run. Do not claim an assessment as completed unless you actually perform it.

## How to use

Choose one scenario and allow 30 minutes. First write what you would ask, what you know, what you would test, and your customer update. Explain your thinking aloud if practising a live interview. Documentation is allowed; record any help used. Read the [review guide](mock-interview-review.md) only after your attempt.

For every scenario, include impact and urgency, evidence versus assumptions, at least two competing hypotheses and discriminating tests, a safe action or escalation, validation and a customer-facing response. Never ask for a customer's secret or promise an unsupported ETA.

## 1. OAuth token failure

A customer says their integration stopped syncing after a credential rotation. Their application reports that the token endpoint returns 401. The separate health endpoint is green.

Illustrative evidence:

- The request is to the identity provider's token endpoint using the client-credentials grant.
- The token endpoint returns `401 invalid_client`.
- Another synthetic client can obtain a token from the same endpoint.
- The customer has not shared their secret, and you have not inspected it.

Questions:

1. Where in the request path is the failure occurring? What does the health result tell you?
2. Give three plausible explanations and a safe way to distinguish them.
3. What would you ask the customer to check without collecting credentials?
4. How would you validate recovery and communicate without claiming a cause prematurely?

## 2. Slow API with healthy readiness

A customer says order-history requests are slow and sometimes return 503. Health and readiness both return 200.

Illustrative evidence from one affected request:

- Its request ID links the API response to an application log showing a query cancellation after approximately two seconds.
- PostgreSQL reports the order query waiting for a relation lock.
- `pg_blocking_pids` identifies a separate session; the lab record shows that session holds an access-exclusive lock on the orders table.
- Other database queries continue to succeed.

Questions:

1. What can you conclude, and which details are still unknown?
2. How would you distinguish lock contention from a bad query plan or network latency?
3. What is a safe response to the blocking session in a disposable exercise? How would real production ownership change your action?
4. What would you validate after the obstruction is removed? Write an initial customer update.

## 3. Webhook replay request

A customer says: “Our provider is back online. Please resend yesterday's order notification.”

Illustrative evidence:

- The order was accepted, and the delivery record is `dead` after the configured retry limit.
- A new order is delivered after the partner recovers.
- The recipient's processing history for the old event has not yet been checked.
- The event has a stable ID and a replay mechanism exists.

Questions:

1. Why does the new delivery succeeding not prove the old delivery recovered?
2. What must you check before replay, and what duplicate risk remains?
3. What is the smallest appropriate action if the recipient has not processed the event? What changes if it already has?
4. What evidence would establish recovery, and what should the customer be told while recipient status is unknown?

## Scoring

For each scenario score 0–2 in each category: triage, reproduction/evidence, hypotheses, root-cause reasoning, safe action, validation, customer communication and internal handoff. Maximum 16. A practice target is 13/16, with no zero in evidence, reasoning or validation. This benchmark is a learning aid, not an employer certification.

Record date, elapsed time, scenario, independent or assisted status, evidence used, score, weak areas and a retest date. Never publish credentials or present generated work as a personal investigation.
