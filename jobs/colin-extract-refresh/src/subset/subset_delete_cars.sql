-- Global delete/clear for cars* tables (subset refresh/load).
-- Intended to be executed while connected to target Postgres extract DB (cprd_pg).
--
-- These tables are NOT corp-scoped, so we truncate the entire dataset and reload from Oracle.
-- Volume is low enough that a full refresh is appropriate.
-- SET search_path TO TARGET_SCHEMA;

TRUNCATE TABLE TARGET_SCHEMA.carindiv;
TRUNCATE TABLE TARGET_SCHEMA.carsrept;
TRUNCATE TABLE TARGET_SCHEMA.carsbox;
TRUNCATE TABLE TARGET_SCHEMA.carsfile;
