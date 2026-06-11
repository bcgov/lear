-- Global delete/clear for cars* tables (subset refresh/load).
-- Intended to be executed while connected to target Postgres extract DB (cprd_pg).
--
-- These tables are NOT corp-scoped, so we truncate the entire dataset and reload from Oracle.
-- Volume is low enough that a full refresh is appropriate.

TRUNCATE TABLE __DBSCHEMA_TARGET_SCHEMA__.carindiv;
TRUNCATE TABLE __DBSCHEMA_TARGET_SCHEMA__.carsrept;
TRUNCATE TABLE __DBSCHEMA_TARGET_SCHEMA__.carsbox;
TRUNCATE TABLE __DBSCHEMA_TARGET_SCHEMA__.carsfile;
