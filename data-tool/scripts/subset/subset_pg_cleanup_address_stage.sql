-- Cleanup the shared address staging table used by subset_transfer_chunk.sql.
-- No-op: the helper table is predeclared in the COLIN extract DDL and is truncated during prepare/chunk execution.

TRUNCATE TABLE __DBSCHEMA_TARGET_SCHEMA__.subset_address_stage;
