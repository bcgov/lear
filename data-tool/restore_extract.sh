#!/usr/bin/env bash
# restore_extract.sh
#
# 1. Drops / regenerates the database from Oracle
# 2. Restores the preserved tables and repairs sequences

set -euo pipefail

##############################################################################
# USER‑TUNABLE PARAMETERS                                               #
##############################################################################

# -- Connection ----------------------------------------------------------------
PGHOST="${PGHOST:-localhost}"        # or ‑‑host
PGPORT="${PGPORT:-5432}"             # or ‑‑port
PGUSER="${PGUSER:-postgres}"        # or ‑‑user
PGDATABASE="${PGDATABASE:-colin-mig-corps-test}"     # or ‑‑dbname
# Supply the password *either* via a .pgpass file *or* one‑shot:
#   PGPASSWORD=secret ./restore_extract.sh
##############################################################################

# -- Tables to restore ------------------------------------------------------------
RESTORE=(corp_processing colin_tracking mig_group mig_batch mig_corp_batch corps_with_third_party)

# -- Runtime options -----------------------------------------------------------
DUMP="${DUMP}"

##############################################################################
# INTERNAL HELPERS
##############################################################################

die() { printf >&2 "error: %s\n" "$*"; exit 1; }

# Build a single “‑h … ‑p … ‑U …” string so every call is consistent
pg_conn_opts() {
  printf -- "-h %s -p %s -d %s -U %s" "$PGHOST" "$PGPORT" "$PGDATABASE" "$PGUSER"
}

# Pass arrays (e.g., KEEP) as repeated --table switches
as_table_opts() { local t; for t in "$@"; do printf -- '--table=%s ' "$t"; done; }


##############################################################################
# ── RECREATE THE DATABASE FROM ORACLE                                       #
##############################################################################

# TODO: test adding extract script reference here.  i.e. /data-tool/scripts/transfer_cprd_corps.sql
printf "🔄  Re‑importing Postgres from Oracle …\n"

##############################################################################
# -- EMPTY the tables but keep their structure                               #
##############################################################################
printf "🧹  Truncating existing rows …\n"
psql $(pg_conn_opts) -v ON_ERROR_STOP=1 -q <<SQL
  TRUNCATE TABLE $(IFS=,; echo "${RESTORE[*]}") RESTART IDENTITY;
SQL
#  - RESTART IDENTITY zeros the sequences; we'll set them correctly later.
#  - No CASCADE → we don’t wipe child tables that reference these rows.

##############################################################################
# ── RESTORE DATA FOR THE PRESERVED TABLES                                   #
##############################################################################

printf "🚚  Copying preserved rows (constraints temporarily disabled) …\n"
pg_restore $(pg_conn_opts) --section=data --data-only \
          --disable-triggers \
          $(as_table_opts "${RESTORE[@]}") "$DUMP"

##############################################################################
# ── FIX ANY SEQUENCES                                                       #
##############################################################################

printf "🛠  Advancing sequences …\n"
psql $(pg_conn_opts) <<'SQL'
DO $$
DECLARE
  r record;
  max_val bigint;
BEGIN
  FOR r IN
    -- For SERIAL/IDENTITY columns (auto-dependency from sequence to column)
    SELECT seq.relname AS seq,
           tbl.relname AS tbl,
           col.attname AS col
    FROM pg_class seq
    JOIN pg_depend d ON d.objid = seq.oid AND d.deptype = 'a'
    JOIN pg_class tbl  ON tbl.oid = d.refobjid
    JOIN pg_attribute col
           ON col.attrelid = tbl.oid AND col.attnum = d.refobjsubid
    WHERE  seq.relkind = 'S'
    UNION ALL
    -- For columns with DEFAULT nextval('sequence') (normal dependency from column default to sequence)
    SELECT
      seq.relname as seq,
      tbl.relname as tbl,
      col.attname as col
    FROM pg_depend d
    JOIN pg_class seq ON seq.oid = d.refobjid AND seq.relkind = 'S'
    JOIN pg_attrdef ad ON ad.oid = d.objid AND d.classid = 'pg_attrdef'::regclass
    JOIN pg_attribute col ON col.attrelid = ad.adrelid AND col.attnum = ad.adnum
    JOIN pg_class tbl ON tbl.oid = ad.adrelid
    WHERE d.deptype = 'n'
  LOOP
    EXECUTE format('SELECT MAX(%I) FROM %I', r.col, r.tbl) INTO max_val;
    IF max_val IS NULL THEN
      -- Table is empty, reset sequence to start at 1. The next call to nextval() will return 1.
      EXECUTE format('SELECT setval(%L, 1, false);', r.seq);
    ELSE
      -- Table has data, set sequence so nextval() returns max_val + 1.
      EXECUTE format('SELECT setval(%L, %s);', r.seq, max_val);
    END IF;
  END LOOP;
END;
$$;
SQL

printf "✅  Done. Preserved tables restored; sequences synchronised.\n"
