# INC-012 — Partner throttles webhook deliveries

Customer: “Our integration accepts orders, but partner notifications have slowed or stopped.”

In a disposable local stack, set `LAB_PARTNER_MODE=rate_limit` and run `docker compose up -d --build --force-recreate partner`. Create one synthetic order. Inspect the worker's attempts and the `deliveries` table. The partner returns HTTP 429 with `Retry-After: 5`; the worker caps a numeric delay at five minutes and stops after five failed attempts. Check that the partner did not record the throttled event.

Switch back to `LAB_PARTNER_MODE=normal` and recreate the partner. For a dead delivery, investigate whether the partner processed the fixed event ID before planning a replay. Explain to the customer the difference between order acceptance and webhook delivery. Document evidence, hypothesis tests, timing, recovery and prevention in [the template](../TEMPLATE.md).

Status: implemented scenario; The injected failure and recovery passed the CI webhook step; learner investigation remains pending. See [verification evidence](../webhook-verification.md). Rate-limit state is a deterministic lab mode, not a realistic shared quota service.

## Collect and validate evidence

Use the order creation example in [operations](../../docs/operations.md), with a unique external ID. Record the returned order ID and UTC time, then inspect `docker compose logs --tail=100 worker partner` and `docker compose exec db psql -U lab -d relaydesk -c "SELECT id,order_id,state,attempts,last_error FROM deliveries;"`. Match the order ID to its delivery. Distinguish a 429 response from a network failure and from a 401 authentication error. Record the retry timing and response evidence rather than assuming a quota cause in a real incident.

After returning the synthetic partner to normal, observe whether a pending retry reaches delivered state. A dead delivery does not automatically recover. Before any replay, check whether the recipient processed the event and consider duplicate side effects. The automated recovery test switches modes before exhaustion; it does not prove dead-letter replay works.
