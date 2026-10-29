-- Disposable local lab only. Adds 50,000 synthetic rows, without an outbox.
-- Baseline and improved timings depend on machine, cache, and PostgreSQL settings.
INSERT INTO orders (id, tenant_id, external_id, status, created_at)
SELECT gen_random_uuid(), 'acme', 'perf-demo-' || n,
       CASE WHEN n % 1000 = 0 THEN 'needs_review' ELSE 'received' END,
       now() - (n * interval '1 second')
FROM generate_series(1, 50000) AS n
ON CONFLICT (tenant_id, external_id) DO NOTHING;
ANALYZE orders;
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, external_id FROM orders WHERE tenant_id = 'acme' AND status = 'needs_review';
-- Create the index after capturing the first actual plan, then rerun EXPLAIN.
CREATE INDEX IF NOT EXISTS orders_tenant_status_lab_idx ON orders (tenant_id, status);
ANALYZE orders;
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, external_id FROM orders WHERE tenant_id = 'acme' AND status = 'needs_review';
