-- Postgres "fast load" session settings for DbSchemaCLI subset extracts.
--
-- These settings apply only to the current session/connection and are intended for
-- disposable extract databases (where maximum durability is not required).
--
-- IMPORTANT:
-- - subset_delete_chunk.sql creates a TEMP table. Any temp-table related settings (e.g. temp_buffers)
--   must be set before the first chunk delete runs.
-- - Keep this file free of DO $$ blocks; some DbSchemaCLI builds split statements on semicolons
--   and don't handle dollar-quoted bodies reliably.

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;

-- Big win for many commits / batched inserts (safe for ephemeral extract DBs).
SET synchronous_commit = off;

-- Optional knobs (uncomment if you know you need them):
-- SET client_min_messages = warning;
-- SET temp_buffers = '64MB';
