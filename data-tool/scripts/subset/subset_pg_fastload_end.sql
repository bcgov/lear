-- Reset session settings set by subset_pg_fastload_begin.sql.

SET synchronous_commit TO DEFAULT;
SET statement_timeout TO DEFAULT;
SET lock_timeout TO DEFAULT;
SET idle_in_transaction_session_timeout TO DEFAULT;

-- If you enabled any optional knobs above, reset them here too:
-- RESET client_min_messages;
-- RESET temp_buffers;
