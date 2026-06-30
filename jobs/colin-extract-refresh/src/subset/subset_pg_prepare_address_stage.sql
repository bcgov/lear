-- Prepare the shared address staging table used by subset_transfer_chunk.sql.
-- This is a predeclared regular table (not TEMP) because DbSchemaCLI transfer work may use separate sessions.
SET search_path TO colin_extract_temp;

TRUNCATE TABLE colin_extract_temp.subset_address_stage;
