# INC-005 — Duplicate signed callback

Customer: "We received the same event twice. Will this duplicate an order?"

With the Compose stack running, create a synthetic order and copy its UUID. Use `python scripts/send_callback.py <order-uuid>` twice with the same event ID, setting `LAB_WEBHOOK_SECRET` to the local Compose secret if overridden. Inspect `duplicate` in both responses and `received_events` in PostgreSQL. Compare with a different event ID. Alter the body without recomputing the signature to check rejection. Explain at-least-once delivery, idempotency, signature validation timestamp freshness, and the difference between the Compose partner's persistent SQLite store and its in-memory test mode.

Status: implemented scenario; PostgreSQL callback deduplication and Compose startup pass CI; learner investigation is pending. Timestamp-bound signatures reject callbacks older than five minutes; the Compose partner keeps its event IDs across restarts, but its standalone in-memory mode does not. Complete [the template](../TEMPLATE.md).

## Event ID collision investigation

Create two synthetic orders with different external IDs. Copy their UUIDs as ORDER_A and ORDER_B. In a disposable Compose stack, use a new event ID for every investigation:

```sh
python scripts/send_callback.py ORDER_A unique-incident-event
python scripts/send_callback.py ORDER_A unique-incident-event
python scripts/send_callback.py ORDER_B unique-incident-event
```

The first response should be 202 with `duplicate: false`, the second 202 with `duplicate: true`, and the third 409 with `event_id_conflict`. Replace the placeholder IDs; the callback secret must match the lab configuration. Inspect `docker compose exec db psql -U lab -d relaydesk -c "SELECT event_id,order_id,received_at FROM received_events;"` and compare request IDs with API logs. Confirm the original event remains associated with the first order. A collision needs investigation with the sender; changing IDs or replaying blindly can cause duplicate processing. This lab compares order IDs, not complete callback payloads.

The collision behavior passed [PostgreSQL integration tests](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40965436762) and an [end-to-end Compose test](https://github.com/kinz0042/cloud-support-engineering-lab/actions/runs/40965896829) using signed HTTP requests. This is test evidence for the simulated lab, not an independently completed learner investigation.
