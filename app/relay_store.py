"""PostgreSQL persistence for the RelayDesk integration service."""
import os
import re
import uuid


class StoreUnavailable(Exception):
    pass


class UnknownOrder(Exception):
    pass


class CallbackConflict(Exception):
    pass


class LeaseLost(Exception):
    pass


class ReplayRejected(Exception):
    pass


def _connect():
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=3, row_factory=dict_row)


def ready():
    try:
        with _connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


def list_orders(tenant):
    try:
        with _connect() as conn:
            return conn.execute(
                "SELECT id::text, external_id, status, created_at::text FROM orders "
                "WHERE tenant_id = %s ORDER BY created_at DESC LIMIT 100", (tenant,)
            ).fetchall()
    except Exception as exc:
        raise StoreUnavailable() from exc


def create_order(tenant, external_id):
    order_id = str(uuid.uuid4())
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                row = cur.execute(
                    "INSERT INTO orders (id, tenant_id, external_id) VALUES (%s, %s, %s) "
                    "ON CONFLICT (tenant_id, external_id) DO UPDATE SET external_id = EXCLUDED.external_id "
                    "RETURNING id::text, external_id, status, created_at::text",
                    (order_id, tenant, external_id),
                ).fetchone()
                cur.execute(
                    "INSERT INTO deliveries (order_id, tenant_id) VALUES (%s, %s) "
                    "ON CONFLICT (order_id) DO NOTHING", (row["id"], tenant)
                )
                return row, row["id"] == order_id
    except Exception as exc:
        raise StoreUnavailable() from exc


def claim_delivery():
    """Atomically lease one due delivery, including expired leases after a crash."""
    with _connect() as conn:
        return conn.execute(
            "WITH due AS (SELECT id FROM deliveries WHERE "
            "(state = 'pending' AND next_attempt_at <= now()) OR "
            "(state = 'leased' AND lease_until < now()) "
            "ORDER BY next_attempt_at LIMIT 1 FOR UPDATE SKIP LOCKED) "
            "UPDATE deliveries SET state='leased', lease_until=now()+interval '30 seconds', "
            "attempts=attempts+1 WHERE id IN (SELECT id FROM due) "
            "RETURNING id, order_id::text, tenant_id, attempts"
        ).fetchone()


def finish_delivery(delivery_id, attempts, success, error_code=None, retry_delay=None):
    # Attempts stay monotonic across replays so an old worker cannot regain a lease.
    delay = retry_delay if retry_delay is not None else min(2 ** min(attempts, 6), 60)
    with _connect() as conn:
        result = conn.execute(
            "UPDATE deliveries SET state=CASE WHEN %s THEN 'delivered' "
            "WHEN attempts >= max_attempts THEN 'dead' ELSE 'pending' END, "
            "lease_until=NULL, last_error=%s, "
            "next_attempt_at=now()+(%s * interval '1 second') "
            "WHERE id=%s AND state='leased' AND attempts=%s RETURNING state",
            (success, error_code, delay, delivery_id, attempts),
        ).fetchone()
        if result is None:
            raise LeaseLost("Delivery lease no longer belongs to this attempt")
    return result["state"]


def inspect_delivery(delivery_id, tenant):
    """Read one tenant-scoped delivery and its replay history without mutating it."""
    with _connect() as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        row = conn.execute(
            "SELECT id, order_id::text, tenant_id, state, attempts, max_attempts, "
            "next_attempt_at::text, lease_until::text, last_error FROM deliveries "
            "WHERE id=%s AND tenant_id=%s", (delivery_id, tenant)
        ).fetchone()
        if row is None:
            return None
        row["event_id"] = "delivery-" + str(row["id"])
        row["replays"] = conn.execute(
            "SELECT actor, reason, previous_attempts, new_max_attempts, created_at::text "
            "FROM delivery_replay_audit WHERE delivery_id=%s ORDER BY id", (delivery_id,)
        ).fetchall()
    return row


def replay_delivery(delivery_id, tenant, expected_attempts, actor, reason, recipient_checked=False):
    """Requeue only the inspected dead delivery, preserving its stable event ID."""
    if not recipient_checked:
        raise ValueError("Recipient processing must be checked before replay")
    if delivery_id < 1 or expected_attempts < 1:
        raise ValueError("Delivery ID and expected attempts must be positive")
    if not isinstance(actor, str) or not re.fullmatch(r"[A-Za-z0-9_.@-]{1,80}", actor):
        raise ValueError("Actor must be a short operator label")
    if not isinstance(reason, str) or not 10 <= len(reason.strip()) <= 240 or not reason.isprintable():
        raise ValueError("Reason must contain 10 to 240 printable characters")
    with _connect() as conn:
        row = conn.execute(
            "UPDATE deliveries SET state='pending', next_attempt_at=now(), lease_until=NULL, "
            "max_attempts=attempts+5 WHERE id=%s AND tenant_id=%s AND state='dead' "
            "AND attempts=%s RETURNING id, order_id::text, tenant_id, state, attempts, max_attempts",
            (delivery_id, tenant, expected_attempts)
        ).fetchone()
        if row is None:
            raise ReplayRejected("Delivery missing, not dead, or changed since inspection")
        conn.execute(
            "INSERT INTO delivery_replay_audit "
            "(delivery_id, actor, reason, previous_attempts, new_max_attempts) VALUES (%s,%s,%s,%s,%s)",
            (delivery_id, actor, reason.strip(), expected_attempts, row["max_attempts"])
        )
        row["event_id"] = "delivery-" + str(row["id"])
    return row


def record_callback(event_id, order_id):
    """Returns True only for a first-seen signed event."""
    from psycopg.errors import ForeignKeyViolation
    try:
        with _connect() as conn:
            row = conn.execute(
                "INSERT INTO received_events (event_id, order_id) VALUES (%s, %s) "
                "ON CONFLICT (event_id) DO NOTHING RETURNING event_id", (event_id, order_id)
            ).fetchone()
            if row is None:
                existing = conn.execute(
                    "SELECT order_id::text AS order_id FROM received_events WHERE event_id = %s", (event_id,)
                ).fetchone()
                if existing is None or existing["order_id"] != order_id:
                    raise CallbackConflict("Event ID belongs to another order")
    except ForeignKeyViolation as exc:
        raise UnknownOrder() from exc
    return row is not None

