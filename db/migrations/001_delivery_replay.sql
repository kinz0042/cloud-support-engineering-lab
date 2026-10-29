-- Additive upgrade for an existing disposable RelayDesk database.
-- Fresh databases already receive these objects from db/init.sql.
BEGIN;
ALTER TABLE deliveries ADD COLUMN IF NOT EXISTS max_attempts integer NOT NULL DEFAULT 5
    CHECK (max_attempts > 0);
CREATE TABLE IF NOT EXISTS delivery_replay_audit (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    delivery_id bigint NOT NULL REFERENCES deliveries(id),
    actor text NOT NULL,
    reason text NOT NULL,
    previous_attempts integer NOT NULL,
    new_max_attempts integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
COMMIT;
