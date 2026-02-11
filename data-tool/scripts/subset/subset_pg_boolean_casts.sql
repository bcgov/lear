-- Postgres helper for DbSchemaCLI subset extracts.
--
-- Problem:
-- DbSchemaCLI transfers from Oracle to Postgres commonly bind Oracle CHAR/VARCHAR values as JDBC VARCHAR.
-- When the TARGET column is BOOLEAN, Postgres does NOT have an assignment cast from VARCHAR/BPCHAR -> BOOLEAN,
-- so inserts like:
--   ... SEND_AR_IND = 't'
-- can fail with:
--   ERROR: column "send_ar_ind" is of type boolean but expression is of type character varying
--
-- Solution:
-- Install IMPLICIT casts for varchar/bpchar -> boolean that use Postgres' standard boolean input rules
-- ('t'/'f', 'true'/'false', '1'/'0', 'yes'/'no', etc).
--
-- NOTE:
-- Some DbSchemaCLI builds appear to mangle the keyword "ASSIGNMENT" when executing scripts, producing
-- Postgres errors like:
--   ERROR: syntax error at or near "ASSIGNMEN"
-- Using IMPLICIT still enables automatic casting for INSERT/UPDATE (it is stronger than ASSIGNMENT),
-- while avoiding that parsing issue.
--
-- IMPORTANT (DbSchemaCLI compatibility):
-- DbSchemaCLI splits statements on semicolons and does not reliably handle semicolons inside dollar-quoted
-- bodies. Keep dollar-quoted bodies free of internal semicolons and avoid DO $$ blocks.

CREATE OR REPLACE FUNCTION public.dbcli_varchar_to_boolean(val varchar)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
STRICT
AS $$
    SELECT (val::text)::boolean
$$;

CREATE OR REPLACE FUNCTION public.dbcli_bpchar_to_boolean(val bpchar)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
STRICT
AS $$
    SELECT (val::text)::boolean
$$;

-- Recreate casts in an idempotent way (Postgres has no CREATE CAST IF NOT EXISTS).
DROP CAST IF EXISTS (varchar AS boolean);
CREATE CAST (varchar AS boolean)
    WITH FUNCTION public.dbcli_varchar_to_boolean(varchar)
    AS IMPLICIT -- DbSchemaCLI workaround: avoid keyword being last token
;

DROP CAST IF EXISTS (bpchar AS boolean);
CREATE CAST (bpchar AS boolean)
    WITH FUNCTION public.dbcli_bpchar_to_boolean(bpchar)
    AS IMPLICIT -- DbSchemaCLI workaround: avoid keyword being last token
;
