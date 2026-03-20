#!/usr/bin/env bash
# reset_colin_extract_views.sh
#
# Plan / drop / reset the COLIN extract derived view layer.
#
# Modes:
#   plan  - print the generated drop SQL only (default)
#   drop  - execute the generated drop SQL only
#   reset - execute the generated drop SQL, then reapply the views DDL
#
# Safety:
#   - scopes drop planning to the allowlisted COLIN derived objects only
#   - hard-fails on wrong object type or unexpected external view/MV dependents
#   - never uses CASCADE
#   - requires --yes for drop/reset modes
#
# Examples:
#   ./data-tool/reset_colin_extract_views.sh \
#     --db colin-mig-corps-test-subset
#
#   ./data-tool/reset_colin_extract_views.sh \
#     --mode reset --yes \
#     --db colin-mig-corps-test-subset \
#     --user some_user \
#     --psql-bin /opt/homebrew/opt/postgresql@15/bin/psql

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GENERATOR_SQL="$ROOT_DIR/scripts/colin_corps_extract_generate_view_drop.sql"
VIEWS_DDL="$ROOT_DIR/scripts/colin_corps_extract_postgres_views_ddl"

PSQL_BIN="${PSQL_BIN:-psql}"
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"
PGDATABASE="${PGDATABASE:-colin-mig-corps-test}"
PGSCHEMA="${PGSCHEMA:-public}"
MODE="plan"
ASSUME_YES="false"
ALLOW_EMPTY="false"

usage() {
  cat <<'USAGE'
Usage: reset_colin_extract_views.sh [options]

Options:
  --mode <plan|drop|reset>   plan=print SQL only (default)
                             drop=execute generated drop SQL only
                             reset=drop and then reapply views DDL
  --db, --dbname <name>      target database name (default: colin-mig-corps-test)
  --host <host>              PostgreSQL host (default: localhost)
  --port <port>              PostgreSQL port (default: 5432)
  --user <user>              PostgreSQL user (default: postgres)
  --schema <schema>          target schema (default: public)
  --psql-bin <path>          psql binary to use (default: psql or $PSQL_BIN)
  --yes                      required for drop/reset execution
  --allow-empty              allow drop/reset when zero allowlisted objects exist
  -h, --help                 show help

Notes:
  - Password handling is delegated to .pgpass or PGPASSWORD.
  - plan mode is safe and does not require --yes.
  - reset mode only resets the view/materialized-view layer; it does not rebuild
    the whole extract database.
  - reset mode currently supports only --schema public because the views DDL is
    not schema-qualified.
USAGE
  return 0
}

die() {
  local message="$*"
  printf >&2 'error: %s\n' "$message"
  exit 1
}

require_command() {
  local command_name="$1"
  command -v "$command_name" >/dev/null 2>&1 || die "required command not found: $command_name"
  return 0
}

psql_cmd=()
setup_psql_cmd() {
  psql_cmd=(
    "$PSQL_BIN"
    -X
    -v ON_ERROR_STOP=1
    -h "$PGHOST"
    -p "$PGPORT"
    -U "$PGUSER"
    -d "$PGDATABASE"
  )
  return 0
}

generate_drop_sql() {
  "${psql_cmd[@]}" -qAt -v "schema_name=$PGSCHEMA" -f "$GENERATOR_SQL"
  return 0
}

schema_exists() {
  local result
  result="$("${psql_cmd[@]}" -qAt -v "schema_name=$PGSCHEMA" <<'SQL'
SELECT 1
FROM pg_namespace
WHERE nspname = :'schema_name'
LIMIT 1;
SQL
)"
  if [[ "$result" == "1" ]]; then
    return 0
  fi
  return 1
}

run_reset_transaction() {
  local search_path="public"
  if [[ -n "${PGOPTIONS:-}" ]]; then
    PGOPTIONS="${PGOPTIONS} -c search_path=${search_path}" "${psql_cmd[@]}" -1 -f "$plan_file" -f "$VIEWS_DDL"
    return 0
  fi

  PGOPTIONS="-c search_path=${search_path}" "${psql_cmd[@]}" -1 -f "$plan_file" -f "$VIEWS_DDL"
  return 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --db|--dbname)
      PGDATABASE="${2:-}"
      shift 2
      ;;
    --host)
      PGHOST="${2:-}"
      shift 2
      ;;
    --port)
      PGPORT="${2:-}"
      shift 2
      ;;
    --user)
      PGUSER="${2:-}"
      shift 2
      ;;
    --schema)
      PGSCHEMA="${2:-}"
      shift 2
      ;;
    --psql-bin)
      PSQL_BIN="${2:-}"
      shift 2
      ;;
    --yes)
      ASSUME_YES="true"
      shift
      ;;
    --allow-empty)
      ALLOW_EMPTY="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

case "$MODE" in
  plan|drop|reset)
    ;;
  *)
    die "invalid mode: $MODE"
    ;;
esac

require_command "$PSQL_BIN"
[[ -f "$GENERATOR_SQL" ]] || die "missing generator SQL: $GENERATOR_SQL"
[[ -f "$VIEWS_DDL" ]] || die "missing views DDL: $VIEWS_DDL"
setup_psql_cmd

if [[ "$MODE" == "reset" && "$PGSCHEMA" != "public" ]]; then
  die "reset mode currently supports only --schema public because the views DDL is not schema-qualified"
fi

if [[ "$MODE" == "reset" ]] && ! schema_exists; then
  die "schema '$PGSCHEMA' does not exist in database '$PGDATABASE'"
fi

tmp_dir="${TMPDIR:-/tmp}"
tmp_dir="${tmp_dir%/}"
plan_db_slug="${PGDATABASE//[^A-Za-z0-9_.-]/_}"
plan_file="$(mktemp "${tmp_dir}/colin-view-drop-plan.${plan_db_slug}.XXXXXX")"
trap 'rm -f "$plan_file"' EXIT

generate_drop_sql > "$plan_file"

drop_count="$(grep -Ec '^[[:space:]]*DROP[[:space:]]+' "$plan_file" || true)"

printf 'Generated drop plan for %s.%s using schema %s:\n' "$PGHOST" "$PGDATABASE" "$PGSCHEMA"
cat "$plan_file"

if [[ "$MODE" == "plan" ]]; then
  exit 0
fi

if [[ "$ASSUME_YES" != "true" ]]; then
  die "--yes is required for mode '$MODE'"
fi

if [[ "$drop_count" == "0" && "$ALLOW_EMPTY" != "true" ]]; then
  die "zero allowlisted COLIN derived objects were found; refusing to run '$MODE' without --allow-empty"
fi

if [[ "$MODE" == "drop" ]]; then
  printf '\nExecuting generated drop plan...\n'
  "${psql_cmd[@]}" -f "$plan_file"
  printf 'Done. Dropped allowlisted COLIN derived objects only.\n'
  exit 0
fi

printf '\nExecuting drop plan and reapplying views DDL in a single transaction...\n'
run_reset_transaction
printf 'Done. COLIN derived view layer has been regenerated.\n'
