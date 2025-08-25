#!/usr/bin/env bash
# restore_extract.sh
#
# Backs up a list of Postgres tables that we want to restore whenever a new COLIN extract is created

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
#   PGPASSWORD=secret ./backup_extract_tables.sh
##############################################################################

# -- Tables to keep ------------------------------------------------------------
KEEP=(corp_processing colin_tracking mig_group mig_batch mig_corp_batch mig_corp_account corps_with_third_party)

# -- Runtime options -----------------------------------------------------------
BACKUP_DIR="${BACKUP_DIR:-/backups}"
DUMP="$BACKUP_DIR/keep_$(date +%F).dump"

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
# BACK UP THE TABLES                                                     #
##############################################################################

printf "📦  Dumping preserved tables …\n"
mkdir -p "$BACKUP_DIR"

pg_dump $(pg_conn_opts) -Fc \
        $(as_table_opts "${KEEP[@]}") \
        --no-owner --no-acl \
        -f "$DUMP"

