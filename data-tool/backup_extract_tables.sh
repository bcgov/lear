#!/usr/bin/env bash
# backup_extract_tables.sh
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
# Optional PostgreSQL client binary directory. Leave empty to use PATH.
# Example: PG_BIN=/opt/homebrew/opt/postgresql@15/bin ./backup_extract_tables.sh
PG_BIN="${PG_BIN:-}"
# Supply the password *either* via a .pgpass file *or* one‑shot:
#   PGPASSWORD=secret ./backup_extract_tables.sh
##############################################################################

# -- Runtime options -----------------------------------------------------------
BACKUP_DIR="${BACKUP_DIR:-/backups}"
DUMP="${DUMP:-$BACKUP_DIR/keep_$(date +%F).dump}"
MANIFEST="$DUMP.manifest.json"

##############################################################################
# INTERNAL HELPERS
##############################################################################

die() { printf >&2 "error: %s\n" "$*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRESERVED_TABLES_CONF="$SCRIPT_DIR/scripts/restore/preserved_tables.conf"

pg_tool() {
  local tool="$1"
  if [[ -n "$PG_BIN" ]]; then
    printf '%s/%s' "${PG_BIN%/}" "$tool"
  else
    printf '%s' "$tool"
  fi
}

PG_DUMP_BIN="$(pg_tool pg_dump)"

# Build a single “‑h … ‑p … ‑U …” string so every call is consistent
pg_conn_opts() {
  printf -- "-h %s -p %s -d %s -U %s" "$PGHOST" "$PGPORT" "$PGDATABASE" "$PGUSER"
}

# Pass arrays (e.g., KEEP) as repeated --table switches
as_table_opts() { local t; for t in "$@"; do printf -- '--table=%s ' "$t"; done; }

load_preserved_tables() {
  local table _rest

  [[ -f "$PRESERVED_TABLES_CONF" ]] || die "missing preserved table config: $PRESERVED_TABLES_CONF"

  KEEP=()
  while read -r table _rest; do
    case "${table:-}" in
      ''|'#'*) continue ;;
      *) KEEP+=("$table") ;;
    esac
  done < "$PRESERVED_TABLES_CONF"

  [[ "${#KEEP[@]}" -gt 0 ]] || die "no preserved tables found in $PRESERVED_TABLES_CONF"
}

sha256_file() {
  local path="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$path" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$path" | awk '{print $1}'
  else
    die "neither sha256sum nor shasum is available to create the manifest"
  fi
}

json_escape() {
  local value="$1"
  value=${value//\\/\\\\}
  value=${value//\"/\\\"}
  value=${value//$'\n'/\\n}
  value=${value//$'\r'/\\r}
  printf '%s' "$value"
}

write_manifest() {
  local sha256="$1"
  local created_at pg_dump_version i
  created_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  pg_dump_version="$("$PG_DUMP_BIN" --version)"

  {
    printf '{\n'
    printf '  "created_at": "%s",\n' "$(json_escape "$created_at")"
    printf '  "created_by_script": "data-tool/backup_extract_tables.sh",\n'
    printf '  "dump_path": "%s",\n' "$(json_escape "$DUMP")"
    printf '  "source": {\n'
    printf '    "host": "%s",\n' "$(json_escape "$PGHOST")"
    printf '    "port": "%s",\n' "$(json_escape "$PGPORT")"
    printf '    "database": "%s",\n' "$(json_escape "$PGDATABASE")"
    printf '    "user": "%s"\n' "$(json_escape "$PGUSER")"
    printf '  },\n'
    printf '  "tables": [\n'
    for i in "${!KEEP[@]}"; do
      if [[ "$i" -gt 0 ]]; then
        printf ',\n'
      fi
      printf '    "%s"' "$(json_escape "${KEEP[$i]}")"
    done
    printf '\n  ],\n'
    printf '  "dump_sha256": "%s",\n' "$(json_escape "$sha256")"
    printf '  "pg_dump_version": "%s"\n' "$(json_escape "$pg_dump_version")"
    printf '}\n'
  } > "$MANIFEST"
}

load_preserved_tables

##############################################################################
# BACK UP THE TABLES                                                     #
##############################################################################

printf "📦  Dumping preserved tables …\n"
mkdir -p "$BACKUP_DIR"

"$PG_DUMP_BIN" $(pg_conn_opts) -Fc \
        $(as_table_opts "${KEEP[@]}") \
        --no-owner --no-acl \
        -f "$DUMP"

printf "🧾  Writing manifest …\n"
write_manifest "$(sha256_file "$DUMP")"
printf "✅  Wrote %s and %s\n" "$DUMP" "$MANIFEST"
