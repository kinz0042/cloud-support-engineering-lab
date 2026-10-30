-- Additive and safe to rerun on the disposable lab database. Existing indexes stay intact.
CREATE INDEX IF NOT EXISTS orders_tenant_created_id_idx ON orders (tenant_id, created_at DESC, id DESC);
