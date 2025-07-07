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
# ── RECREATE THE DATABASE FROM ORACLE                                      #
##############################################################################

# TODO: test adding extract script reference here.  i.e. /data-tool/scripts/transfer_cprd_corps.sql
printf "🔄  Re‑importing Postgres from Oracle …\n"

##############################################################################
# ── RESTORE DATA FOR THE PRESERVED TABLES                                           #
##############################################################################

printf "🚚  Copying preserved rows (constraints temporarily disabled) …\n"
pg_restore $(pg_conn_opts) --section=data --data-only \
          --disable-triggers \
          $(as_table_opts "${RESTORE[@]}") "$DUMP"

##############################################################################
# ── FIX ANY SEQUENCES                                                     #
##############################################################################

printf "🛠   Advancing sequences …\n"
psql $(pg_conn_opts) <<'SQL'
DO $$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT seq.relname AS seq,
           tbl.relname AS tbl,
           col.attname AS col
    FROM   pg_class seq
    JOIN   pg_depend d   ON d.objid = seq.oid AND d.deptype = 'a'
    JOIN   pg_class tbl  ON tbl.oid = d.refobjid
    JOIN   pg_attribute col
           ON col.attrelid = tbl.oid AND col.attnum = d.refobjsubid
    WHERE  seq.relkind = 'S'
  LOOP
    EXECUTE format(
      'SELECT setval(%L, COALESCE((SELECT MAX(%I) FROM %I), 0));',
      r.seq, r.col, r.tbl
    );
  END LOOP;
END;
$$;
SQL

printf "✅  Done. Preserved tables restored; sequences synchronised.\n"
