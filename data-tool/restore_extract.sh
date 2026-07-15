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
# Optional PostgreSQL client binary directory. Leave empty to use PATH.
# Example: PG_BIN=/opt/homebrew/opt/postgresql@15/bin ./restore_extract.sh
PG_BIN="${PG_BIN:-}"
# Supply the password *either* via a .pgpass file *or* one‑shot:
#   PGPASSWORD=secret ./restore_extract.sh
##############################################################################

# -- Runtime options -----------------------------------------------------------
DUMP="${DUMP:-}"
DELTA_MODE="${DELTA_MODE:-false}"

##############################################################################
# INTERNAL HELPERS
##############################################################################

die() { printf >&2 "error: %s\n" "$*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRESERVED_TABLES_CONF="$SCRIPT_DIR/scripts/restore/preserved_tables.conf"
REPAIR_SEQUENCES_SQL="$SCRIPT_DIR/scripts/restore/repair_sequences.sql"
DELTA_RESTORE_SCRIPT="$SCRIPT_DIR/delta_restore_extract.sh"

pg_tool() {
  local tool="$1"
  if [[ -n "$PG_BIN" ]]; then
    printf '%s/%s' "${PG_BIN%/}" "$tool"
  else
    printf '%s' "$tool"
  fi
}

PSQL_BIN="$(pg_tool psql)"
PG_RESTORE_BIN="$(pg_tool pg_restore)"

# Build a single “‑h … ‑p … ‑U …” string so every call is consistent
pg_conn_opts() {
  printf -- "-h %s -p %s -d %s -U %s" "$PGHOST" "$PGPORT" "$PGDATABASE" "$PGUSER"
}

# Pass arrays (e.g., RESTORE) as repeated --table switches
as_table_opts() { local t; for t in "$@"; do printf -- '--table=%s ' "$t"; done; }

load_preserved_tables() {
  local table _rest

  [[ -f "$PRESERVED_TABLES_CONF" ]] || die "missing preserved table config: $PRESERVED_TABLES_CONF"

  RESTORE=()
  while read -r table _rest; do
    case "${table:-}" in
      ''|'#'*) continue ;;
      *) RESTORE+=("$table") ;;
    esac
  done < "$PRESERVED_TABLES_CONF"

  [[ "${#RESTORE[@]}" -gt 0 ]] || die "no preserved tables found in $PRESERVED_TABLES_CONF"
}

##############################################################################
# ── ARGUMENTS / DELTA GUARDS                                                #
##############################################################################

delta_requested=false
delta_args=()
for arg in "$@"; do
  case "$arg" in
    --delta)
      delta_requested=true
      ;;
    *)
      delta_args+=("$arg")
      ;;
  esac
done

if [[ "$delta_requested" = "true" ]]; then
  if [[ -f "$DELTA_RESTORE_SCRIPT" ]]; then
    exec bash "$DELTA_RESTORE_SCRIPT" "${delta_args[@]}"
  fi
  die "--delta requested, but $DELTA_RESTORE_SCRIPT is not available yet. Use data-tool/delta_restore_extract.sh when it is added."
fi

if [[ "${#delta_args[@]}" -gt 0 ]]; then
  die "unknown argument(s): ${delta_args[*]}"
fi

if [[ "$DELTA_MODE" = "true" ]]; then
  die "DELTA_MODE=true is no longer supported by restore_extract.sh. Use data-tool/delta_restore_extract.sh instead."
fi

[[ -n "$DUMP" ]] || die "DUMP is required, e.g. DUMP=/backups/keep_YYYY-MM-DD.dump ./restore_extract.sh"
[[ -f "$REPAIR_SEQUENCES_SQL" ]] || die "missing sequence repair SQL: $REPAIR_SEQUENCES_SQL"
load_preserved_tables

##############################################################################
# ── RECREATE THE DATABASE FROM ORACLE                                       #
##############################################################################

# TODO: test adding extract script reference here.  i.e. /data-tool/scripts/transfer_cprd_corps.sql
printf "🔄  Re‑importing Postgres from Oracle …\n"

##############################################################################
# -- EMPTY the tables but keep their structure                               #
##############################################################################
printf "🧹  Truncating existing rows …\n"
printf "Truncating preserved tables.\n"
"$PSQL_BIN" $(pg_conn_opts) -v ON_ERROR_STOP=1 -q <<SQL
TRUNCATE TABLE $(IFS=,; echo "${RESTORE[*]}") RESTART IDENTITY;
SQL
#  - RESTART IDENTITY zeros the sequences; we'll set them correctly later.
#  - No CASCADE → we don’t wipe child tables that reference these rows.

##############################################################################
# ── RESTORE DATA FOR THE PRESERVED TABLES                                   #
##############################################################################
printf "🚚  Copying preserved rows (constraints temporarily disabled) …\n"
"$PG_RESTORE_BIN" $(pg_conn_opts) --section=data --data-only \
          --disable-triggers \
          $(as_table_opts "${RESTORE[@]}") "$DUMP"

##############################################################################
# ── FIX ANY SEQUENCES                                                       #
##############################################################################

printf "🛠  Advancing sequences …\n"
"$PSQL_BIN" $(pg_conn_opts) -f "$REPAIR_SEQUENCES_SQL"

printf "✅  Done. Preserved tables restored; sequences synchronised.\n"
