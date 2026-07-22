-- Invoke the address-transpose orchestrator once at the end of a subset
-- load/refresh while the shared advisory lock is still held.
--
-- IMPORTANT (DbSchemaCLI compatibility):
-- - Plain statements only; no DO $$ blocks, dollar quoting, or client scripting.
-- - The phase procedures COMMIT internally, so CALL must be top-level.
-- - This terminal result-bearing CALL returns one JSON value with phase counts, their total, and elapsed seconds.

SET search_path TO public;

CALL public.colin_address_transpose(NULL);
