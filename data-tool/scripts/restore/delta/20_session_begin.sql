-- Delta restore staging/apply session settings.
-- These settings are scoped to the current psql session/transaction.

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET synchronous_commit = off;
SET work_mem = '512MB';
