# INC-006 — Slow order lookup

**Synthetic customer:** "The review queue has slowed as our order history grew. Can you investigate?"

Environment: disposable RelayDesk PostgreSQL database. The script `sql/slow_orders.sql` inserts 50,000 synthetic rows, captures a query plan, creates a lab index and captures a second plan. Run it with `docker compose exec -T db psql -v ON_ERROR_STOP=1 -U lab -d relaydesk < sql/slow_orders.sql` from a shell that supports input redirection. Capture the actual output, PostgreSQL version, row counts and environment. Explain the plan, buffers and timing observed; don't invent a speedup. The optimizer may choose differently depending on data and cache.

Investigate selectivity, existing indexes, write overhead, and whether the improvement applies to the customer's real query. Consider a rollback plan before creating an index in a real system; this lab index can be removed with `DROP INDEX orders_tenant_status_lab_idx`. The script changes lab data and is safe only for disposable environments. Synthetic rows do not create delivery records. Fill in the investigation template and provide a customer update and engineering handoff.

Status: authored drill; full PostgreSQL execution pending CI validation. This is a simulated scenario, not a real customer case.
