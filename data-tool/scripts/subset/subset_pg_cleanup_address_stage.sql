-- Cleanup the shared address staging table used by subset_transfer_chunk.sql.
-- This is schema-qualified because generated subset runs may target non-public schemas.

TRUNCATE TABLE __DBSCHEMA_TARGET_SCHEMA__.subset_address_stage;
