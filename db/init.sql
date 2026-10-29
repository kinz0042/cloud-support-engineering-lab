CREATE TABLE tenants (id text PRIMARY KEY, display_name text NOT NULL);
INSERT INTO tenants (id, display_name) VALUES ('acme', 'Acme Demo'), ('orbit', 'Orbit Demo');
CREATE TABLE orders (
    id uuid PRIMARY KEY,
    tenant_id text NOT NULL REFERENCES tenants(id),
    external_id text NOT NULL,
    status text NOT NULL DEFAULT 'received',
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, external_id)
);
CREATE INDEX orders_tenant_created_idx ON orders (tenant_id, created_at DESC);
CREATE TABLE deliveries (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id uuid NOT NULL UNIQUE REFERENCES orders(id),
    tenant_id text NOT NULL REFERENCES tenants(id),
    state text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending', 'leased', 'delivered', 'dead')),
    attempts integer NOT NULL DEFAULT 0,
    next_attempt_at timestamptz NOT NULL DEFAULT now(),
    lease_until timestamptz,
    last_error text
);
CREATE INDEX deliveries_due_idx ON deliveries (next_attempt_at) WHERE state = 'pending';
CREATE TABLE received_events (
    event_id text PRIMARY KEY,
    order_id uuid NOT NULL REFERENCES orders(id),
    received_at timestamptz NOT NULL DEFAULT now()
);
