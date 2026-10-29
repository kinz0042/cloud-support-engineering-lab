# INC-004 — Partner webhook rejects delivery

Customer: "The order was accepted, but the partner did not see it."

Start with `LAB_PARTNER_MODE=reject docker compose up -d --build` in a disposable lab. Create an order and compare the API 201 response with the worker's `delivery_attempt` logs, partner 503 response, and the `deliveries` table. Attempts use bounded backoff and enter `dead` after five failures. Set `LAB_PARTNER_MODE=normal` and recreate only the partner; dead deliveries require an explicit, reviewed replay. A 201 confirms persistence, not webhook delivery.

Inspect the queue with `docker compose exec db psql -U lab -d relaydesk -c "SELECT id,state,attempts,last_error FROM deliveries;"`. Before any replay, verify the partner's state and whether it already processed the event. Use the fixed event ID to make repeats safe. Document a customer update, engineering escalation, recovery decision, and validation. Complete [the template](../TEMPLATE.md).

Status: implemented scenario; Docker/PostgreSQL integration execution still needs verification. Do not replay blindly.
