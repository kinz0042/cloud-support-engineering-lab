# INC-005 — Duplicate signed callback

Customer: "We received the same event twice. Will this duplicate an order?"

With the Compose stack running, create a synthetic order and copy its UUID. Use `python scripts/send_callback.py <order-uuid>` twice with the same event ID, setting `LAB_WEBHOOK_SECRET` to the local Compose secret if overridden. Inspect `duplicate` in both responses and `received_events` in PostgreSQL. Compare with a different event ID. Alter the body without recomputing the signature to check rejection. Explain at-least-once delivery, idempotency, signature validation timestamp freshness, and the mock partner's in-memory deduplication limitation.

Status: implemented scenario; PostgreSQL callback deduplication and Compose startup pass CI; learner investigation is pending. Timestamp-bound signatures reject callbacks older than five minutes; the partner's in-memory duplicate set does not survive a restart. Complete [the template](../TEMPLATE.md).
