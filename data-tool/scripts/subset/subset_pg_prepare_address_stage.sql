-- Prepare the shared address staging table used by subset_transfer_chunk.sql.
-- This is a predeclared regular table (not TEMP) because DbSchemaCLI transfer work may use separate sessions.

TRUNCATE TABLE public.subset_address_stage;
