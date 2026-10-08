-- Adds device_id to the existing tree_pins/tree_messages tables (Epic 7
-- hardening) so a pin and its messages can be tied to a device credential -
-- see device_credentials in 004_device_credentials.sql and the DEVICE
-- CREDENTIALS note in backend/app/routers/care.py.
-- Apply to the shared database by hand; the test suite and local seed read
-- schema.sql, which carries the same columns. Existing rows get a null
-- device_id and are treated as ownerless (open to any device).

ALTER TABLE tree_pins ADD COLUMN IF NOT EXISTS device_id TEXT;
ALTER TABLE tree_messages ADD COLUMN IF NOT EXISTS device_id TEXT;

CREATE INDEX IF NOT EXISTS idx_tree_pins_device ON tree_pins(device_id, created_at);
CREATE INDEX IF NOT EXISTS idx_tree_messages_device ON tree_messages(device_id, created_at);
