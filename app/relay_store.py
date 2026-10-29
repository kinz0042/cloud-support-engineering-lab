"""PostgreSQL persistence for the RelayDesk integration service."""
import os
import uuid


class StoreUnavailable(Exception):
    pass


class UnknownOrder(Exception):
    pass


class LeaseLost(Exception):
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
    state = "delivered" if success else "dead" if attempts >= 5 else "pending"
    delay = retry_delay if retry_delay is not None else min(2 ** attempts, 60)
    with _connect() as conn:
        result = conn.execute(
            "UPDATE deliveries SET state=%s, lease_until=NULL, last_error=%s, "
            "next_attempt_at=now()+(%s * interval '1 second') "
            "WHERE id=%s AND state='leased' AND attempts=%s RETURNING id",
            (state, error_code, delay, delivery_id, attempts),
        ).fetchone()
        if result is None:
            raise LeaseLost("Delivery lease no longer belongs to this attempt")
    return state


def record_callback(event_id, order_id):
    """Returns True only for a first-seen signed event."""
    from psycopg.errors import ForeignKeyViolation
    try:
        with _connect() as conn:
            row = conn.execute(
                "INSERT INTO received_events (event_id, order_id) VALUES (%s, %s) "
                "ON CONFLICT (event_id) DO NOTHING RETURNING event_id", (event_id, order_id)
            ).fetchone()
    except ForeignKeyViolation as exc:
        raise UnknownOrder() from exc
    return row is not None
