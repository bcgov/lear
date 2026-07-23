\set ON_ERROR_STOP on

/*
One-time DBA provisioning for a restricted COLIN extract owner.

Run from a maintenance database as a PostgreSQL superuser:

  psql -X -v ON_ERROR_STOP=1 -d postgres \
    -v role=colin_extract -v dbname=colin_extract \
    -f data-tool/scripts/bootstrap/colin_extract_restricted_bootstrap.sql

This file intentionally does not accept or store a password. Configure LOGIN
authentication with the deployment's approved secret-management process.

After this file succeeds:
  1. connect as the restricted role and apply
     colin_corps_extract_postgres_ddl, then
     colin_corps_extract_postgres_views_ddl;
  2. reconnect as a superuser and install
     ../subset/subset_pg_boolean_casts.sql once in this database.

The cast installer is separate so the extract objects remain owned by the
restricted role while the pg_catalog casts and their conversion functions are
owned by the bootstrap superuser.
*/

\if :{?role}
\else
  \echo 'ERROR: required psql variable "role" is missing (use -v role=...)'
  \quit 3
\endif

\if :{?dbname}
\else
  \echo 'ERROR: required psql variable "dbname" is missing (use -v dbname=...)'
  \quit 3
\endif

SELECT rolsuper AS bootstrap_is_superuser
FROM pg_catalog.pg_roles
WHERE rolname = current_user
\gset

\if :bootstrap_is_superuser
\else
  \echo 'ERROR: this bootstrap must be run by a PostgreSQL superuser'
  \quit 3
\endif

-- Never mutate the bootstrap identity or silently de-privilege an existing
-- administrative role because of a mistyped -v role=... value.
SELECT NOT EXISTS (
    SELECT 1
    FROM pg_catalog.pg_roles
    WHERE rolname = :'role'
      AND (
          rolname = current_user
          OR rolsuper
          OR rolcreatedb
          OR rolcreaterole
          OR rolreplication
          OR rolbypassrls
      )
) AS target_role_is_safe
\gset

\if :target_role_is_safe
\else
  \echo 'ERROR: target role is the bootstrap identity or already has privileged attributes'
  \quit 3
\endif

-- CREATE ROLE has no IF NOT EXISTS form. \gexec makes this rerunnable.
SELECT pg_catalog.format(
    'CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',
    :'role'
)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_catalog.pg_roles
    WHERE rolname = :'role'
)
\gexec

-- Normalize an existing bootstrap role to the intended steady-state attributes.
ALTER ROLE :"role"
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS;

-- CREATE DATABASE also has no IF NOT EXISTS form and cannot run in a transaction.
SELECT pg_catalog.format(
    'CREATE DATABASE %I OWNER %I TEMPLATE template0',
    :'dbname',
    :'role'
)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_catalog.pg_database
    WHERE datname = :'dbname'
)
\gexec

-- Existing empty databases can be adopted by rerunning this bootstrap.
ALTER DATABASE :"dbname" OWNER TO :"role";

\connect :dbname

-- The role must own public before it applies either DDL, so every created
-- table, sequence, view, materialized view, function, and procedure is role-owned.
ALTER SCHEMA public OWNER TO :"role";

\echo 'Restricted role/database/schema provisioning complete.'
\echo 'Next: apply both COLIN DDL files as the restricted role.'
\echo 'Then: install subset/subset_pg_boolean_casts.sql in this DB as superuser.'
