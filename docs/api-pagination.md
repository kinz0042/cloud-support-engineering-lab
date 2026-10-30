# Missing orders: pagination investigation

This is a synthetic integration scenario for the disposable RelayDesk Compose profile. The previous implementation returned only the newest 100 orders with no continuation field. The current API exposes a bounded cursor so an integration can request subsequent pages. This is a project change, not a real customer incident or proof of an independently completed learner investigation.

## How it works

`GET /v1/orders` defaults to at most 100 tenant-scoped results. `limit` accepts an integer from 1 to 100. A response has `orders`, `request_id` and `next_cursor`; a non-null cursor points to the last returned `(created_at, id)` position. Send it as the next request's `cursor` parameter, retaining the appropriate tenant credential. A null cursor indicates no more rows were found by that request.

PostgreSQL orders by `created_at DESC, id DESC`; the unique ID breaks timestamp ties. The query retrieves one extra row to decide whether another page exists. The index on `(tenant_id, created_at DESC, id DESC)` supports the access pattern. Every query filters by the authenticated tenant; a cursor is a client-controlled position, not permission to read another tenant. It is encoded but unsigned and unencrypted. Do not treat it as confidential or authoritative.

This is keyset pagination, **not a point-in-time snapshot**. Newly inserted rows ahead of an existing cursor can be missed in that traversal, and updates or deletions can affect the result. A production export or continuous integration needs a separately designed snapshot, reconciliation or change-tracking approach. Do not promise completeness during concurrent changes based solely on this cursor. The demo OAuth gateway and the pagination client each bound an upstream page at 256 KiB; an oversized gateway response yields 502, while the client reports an error. Investigate unexpectedly large rows or use a smaller page rather than disabling the bound.

## Reproduce in a disposable lab

Start the [Docker profile](operations.md) with a disposable database. The following Bash command inserts 105 synthetic Acme orders with the same timestamp to exercise the tie-breaker. They are inserted directly into the database for investigation and deliberately do **not** enqueue webhooks. Use only the isolated lab; the command modifies its database.

```bash
docker compose exec -T db psql -v ON_ERROR_STOP=1 -U lab -d relaydesk <<'SQL'
INSERT INTO orders (id, tenant_id, external_id, created_at)
SELECT gen_random_uuid(), 'acme', 'pagination-lab-' || n,
       TIMESTAMPTZ '2026-01-01 00:00:00+00'
FROM generate_series(1, 105) AS n
ON CONFLICT (tenant_id, external_id) DO NOTHING;
SQL
```

If the lab already contains Acme orders, the client count includes them. Inspect the fixture count separately:

```bash
docker compose exec -T db psql -U lab -d relaydesk -c "SELECT count(*) FROM orders WHERE tenant_id = 'acme' AND external_id LIKE 'pagination-lab-%';"
curl -i -H 'Authorization: Bearer acme-local-key' 'http://127.0.0.1:8081/v1/orders?limit=25'
python scripts/paginate_orders.py --tenant acme --limit 25
python scripts/paginate_orders.py --tenant orbit --limit 25
```

The read-only client follows cursors on the fixed loopback API and prints only counts, not tokens or response bodies. It uses the default public Compose demo keys; changing those keys requires a separate manual investigation. It stops on repeated cursors, duplicate order IDs, invalid responses, redirects or its page limit. Acme's total should cover the fixture; Orbit must not receive Acme orders. Compare the response request IDs and tenant-specific database evidence rather than assuming a customer has lost data. The client is a lab diagnostic, not a production synchronization tool.

For Windows PowerShell use `curl.exe`; the SQL here-document above is Bash syntax. If needed, pass a PowerShell here-string to `docker compose exec -T db psql` instead. Do not blindly delete shared data; the inserted fixtures persist in the lab volume. `docker compose down` keeps that volume, while `down -v` removes it and all its data.

For an existing **disposable lab volume**, review [migration 002](../db/migrations/002_orders_pagination_index.sql), then run the following from the repository root in Bash:

```bash
docker compose exec -T db psql -v ON_ERROR_STOP=1 -U lab -d relaydesk < db/migrations/002_orders_pagination_index.sql
```

In Windows PowerShell, use:

```powershell
Get-Content -Raw .\db\migrations\002_orders_pagination_index.sql | docker compose exec -T db psql -v ON_ERROR_STOP=1 -U lab -d relaydesk
```

The migration adds the pagination index and is safe to repeat on the disposable lab. It is an ordinary index build and can block writes; do not run it on a real database without a separately reviewed deployment plan. Correct pagination does not depend on the index existing. The PowerShell migration command has not been verified on the learner's laptop.

## Support workflow

Scope the customer, time range, expected count and API credential without collecting the secret. Reproduce the request; inspect `next_cursor`, status, request ID, page size and the integration's page-handling logs. Compare hypotheses: first-page-only client, tenant mismatch, concurrent inserts, a restrictive query or genuinely absent records. Check a tenant-scoped count and a second page before claiming data loss. Acknowledge that the records may exist even when a client has not fetched them.

Validate every page once against an unchanged synthetic dataset, including equal timestamps and another tenant's negative control. For changing data, identify what the cursor cannot guarantee. Record your own evidence, fix or client guidance, validation, customer update and engineering handoff in [INC-021](../incidents/INC-021/brief.md). Never publish bearer keys, raw customer records or unredacted cursor contents.
