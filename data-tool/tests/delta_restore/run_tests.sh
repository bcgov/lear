#!/usr/bin/env bash
# Lightweight delta restore harness.
#
# Static/AWK checks always run. PostgreSQL-backed checks run only when local
# libpq tooling is present and reachable; otherwise they are skipped with a
# clear message so this harness is safe on workstations/CI without Postgres.

set -u -o pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
DATA_TOOL_DIR="$ROOT_DIR/data-tool"
TEST_DIR="$DATA_TOOL_DIR/tests/delta_restore"
FIXTURES_DIR="$TEST_DIR/fixtures"
EXPECTED_DIR="$TEST_DIR/expected"
TMP_BASE="${TMPDIR:-/tmp}/delta_restore_tests.$$"

PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"
PG_BIN="${PG_BIN:-}"
PGDATABASE_ADMIN="${DELTA_RT_ADMIN_DB:-postgres}"
KEEP_DBS="${DELTA_RT_KEEP_DBS:-false}"
RUN_INTEGRATION="${DELTA_RT_RUN_INTEGRATION:-false}"

pass_count=0
fail_count=0
skip_count=0
created_dbs=""

usage() {
  cat <<'USAGE'
Usage: run_tests.sh [--integration] [--static-only] [--keep-dbs] [-h|--help]

Checks:
  static       Shell syntax and guarded COPY-header AWK happy/failure paths.
  sql-smoke    If local Postgres tooling is available: compile/install delta SQL
               and run a focused preserved-parent BLOCKED_FK smoke fixture.
  integration  Optional: create source/local throwaway DBs with minimal DDL,
               run backup -> preview -> apply for an identical dump scenario.

Environment:
  PGHOST, PGPORT, PGUSER, PGPASSWORD/PGPASSFILE   libpq connection settings
  PG_BIN=/path/to/postgres/bin                    optional PostgreSQL client binary directory
  DELTA_RT_ADMIN_DB=postgres                      admin DB for createdb checks
  DELTA_RT_RUN_INTEGRATION=true                   same as --integration
  DELTA_RT_KEEP_DBS=true                          keep throwaway DBs on failure
  DELTA_RT_T11_NK_HASH_JOIN_PERF_MAX_MS=60000      t11 runtime ceiling in milliseconds
USAGE
  return 0
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --integration) RUN_INTEGRATION="true"; shift ;;
    --static-only) RUN_INTEGRATION="false"; PG_SMOKE_DISABLED="true"; shift ;;
    --keep-dbs) KEEP_DBS="true"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf >&2 "unknown argument: %s\n" "$1"; usage >&2; exit 2 ;;
  esac
done

mkdir -p "$TMP_BASE"

pg_tool() {
  local tool="$1"
  if [[ -n "$PG_BIN" ]]; then
    printf '%s/%s' "${PG_BIN%/}" "$tool"
  else
    printf '%s' "$tool"
  fi
  return 0
}

PSQL_BIN="$(pg_tool psql)"
PG_DUMP_BIN="$(pg_tool pg_dump)"
PG_RESTORE_BIN="$(pg_tool pg_restore)"
CREATEDB_BIN="$(pg_tool createdb)"
DROPDB_BIN="$(pg_tool dropdb)"

log() { printf '%s\n' "$*"; return 0; }
pass() { pass_count=$((pass_count + 1)); printf 'ok - %s\n' "$*"; return 0; }
fail() { fail_count=$((fail_count + 1)); printf 'not ok - %s\n' "$*"; return 0; }
skip() { skip_count=$((skip_count + 1)); printf 'skip - %s\n' "$*"; return 0; }

cleanup() {
  local db
  if [[ "$KEEP_DBS" != "true" ]]; then
    for db in $created_dbs; do
      "$DROPDB_BIN" -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" --if-exists "$db" >/dev/null 2>&1 || true
    done
  elif [[ -n "$created_dbs" ]]; then
    printf 'Keeping throwaway DBs: %s\n' "$created_dbs"
  fi
  rm -rf "$TMP_BASE"
  return 0
}
trap cleanup EXIT

require_file() {
  local path="$1"
  [[ -f "$path" ]] || { fail "missing required file: $path"; return 1; }
  return 0
}

run_static_checks() {
  log '== static checks =='
  local ok=true
  for f in \
    "$DATA_TOOL_DIR/delta_restore_extract.sh" \
    "$DATA_TOOL_DIR/backup_extract_tables.sh" \
    "$DATA_TOOL_DIR/restore_extract.sh" \
    "$TEST_DIR/run_tests.sh"; do
    if bash -n "$f"; then
      pass "bash -n ${f#$ROOT_DIR/}"
    else
      fail "bash -n ${f#$ROOT_DIR/}"
      ok=false
    fi
  done

  local awk_tmp expected sidecar out err
  awk_tmp="$TMP_BASE/awk"
  mkdir -p "$awk_tmp"
  expected="$awk_tmp/expected.txt"
  sidecar="$awk_tmp/sidecar.tsv"
  out="$awk_tmp/out.sql"
  err="$awk_tmp/err.txt"
  printf 'mig_group\n' > "$expected"

  cat > "$awk_tmp/happy.sql" <<'SQL'
SET transaction_timeout = 0;
COPY public.mig_group (id, name, target_environment, source_db) FROM stdin;
1	group	dev	COLIN
\.
SQL
  if awk -f "$DATA_TOOL_DIR/scripts/restore/delta/rewrite_copy_targets.awk" \
        -v sidecar="$sidecar" -v expected="$expected" \
        "$awk_tmp/happy.sql" > "$out" 2> "$err" \
     && grep -q 'COPY delta_stage.mig_group' "$out" \
     && grep -q 'skipped unsupported client-only setting' "$out" \
     && grep -q $'mig_group\tid,name,target_environment,source_db' "$sidecar"; then
    pass 'AWK rewrite happy path captures sidecar, retargets COPY, and filters unsupported SET'
  else
    fail 'AWK rewrite happy path'
    ok=false
  fi

  cat > "$awk_tmp/unexpected.sql" <<'SQL'
COPY public.not_preserved (id) FROM stdin;
1
\.
SQL
  if awk -f "$DATA_TOOL_DIR/scripts/restore/delta/rewrite_copy_targets.awk" \
        -v sidecar="$sidecar" -v expected="$expected" \
        "$awk_tmp/unexpected.sql" > "$out" 2> "$err"; then
    fail 'AWK rewrite rejects unexpected COPY table'
    ok=false
  elif grep -q 'not expected' "$err"; then
    pass 'AWK rewrite rejects unexpected COPY table'
  else
    fail 'AWK rewrite failure path produced unclear error'
    ok=false
  fi

  [[ "$ok" = "true" ]]
  return $?
}

tool_available() {
  local tool="$1"
  case "$tool" in
    */*) [[ -x "$tool" ]] ;;
    *) command -v "$tool" >/dev/null 2>&1 ;;
  esac
  return $?
}

have_pg_tools() {
  tool_available "$PSQL_BIN" && \
  tool_available "$CREATEDB_BIN" && \
  tool_available "$DROPDB_BIN" && \
  tool_available "$PG_DUMP_BIN" && \
  tool_available "$PG_RESTORE_BIN"
  return $?
}

can_connect_pg() {
  "$PSQL_BIN" -X -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE_ADMIN" -v ON_ERROR_STOP=1 -qAt -c 'SELECT 1' >/dev/null 2>&1
  return $?
}

create_db() {
  local db="$1"
  "$DROPDB_BIN" -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" --if-exists "$db" >/dev/null 2>&1 || true
  "$CREATEDB_BIN" -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -T template0 "$db"
  created_dbs="$created_dbs $db"
  return 0
}

psql_db() {
  local db="$1"
  shift
  "$PSQL_BIN" -X -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$db" -v ON_ERROR_STOP=1 "$@"
  return $?
}

run_sql_smoke() {
  log '== sql smoke =='
  if [[ "${PG_SMOKE_DISABLED:-false}" = "true" ]]; then
    skip 'Postgres SQL smoke disabled by --static-only'
    return 0
  fi
  if ! have_pg_tools; then
    skip 'Postgres SQL smoke: psql/createdb/dropdb/pg_dump/pg_restore not all available; set PG_BIN if needed'
    return 0
  fi
  if ! can_connect_pg; then
    skip "Postgres SQL smoke: cannot connect to $PGHOST:$PGPORT/$PGDATABASE_ADMIN as $PGUSER"
    return 0
  fi

  local db="delta_rt_compile_$$"
  if ! create_db "$db"; then
    skip "Postgres SQL smoke: could not create throwaway DB $db"
    return 0
  fi

  if psql_db "$db" -v "t11_nk_hash_join_perf_max_ms=${DELTA_RT_T11_NK_HASH_JOIN_PERF_MAX_MS:-60000}" \
       -f "$DATA_TOOL_DIR/scripts/restore/delta/00_install.sql" \
       -f "$DATA_TOOL_DIR/scripts/restore/delta/10_functions.sql" \
       -f "$FIXTURES_DIR/minimal_schema.sql" \
       -f "$FIXTURES_DIR/t08_blocked_fk_smoke.sql" \
       -f "$EXPECTED_DIR/t08_blocked_fk_assert.sql" \
       -f "$FIXTURES_DIR/t09_unenforced_nk_ambiguity.sql" \
       -f "$EXPECTED_DIR/t09_unenforced_nk_ambiguity_assert.sql" \
       -f "$FIXTURES_DIR/t10_auth_component_local_only.sql" \
       -f "$EXPECTED_DIR/t10_auth_component_local_only_assert.sql" \
       -f "$FIXTURES_DIR/t11_nk_hash_join_perf.sql" \
       -f "$EXPECTED_DIR/t11_nk_hash_join_perf_assert.sql" >/dev/null; then
    pass 'SQL compile + classification performance smoke'
  else
    fail 'SQL compile + classification performance smoke'
    return 1
  fi
}

latest_run_dir() {
  local base="$1"
  find "$base" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort | tail -n 1
  return $?
}

run_optional_integration() {
  log '== optional integration =='
  if [[ "$RUN_INTEGRATION" != "true" ]]; then
    skip 'integration: set DELTA_RT_RUN_INTEGRATION=true or pass --integration to run backup/preview/apply smoke'
    return 0
  fi
  if ! have_pg_tools || ! can_connect_pg; then
    skip 'integration: Postgres tooling/connectivity unavailable'
    return 0
  fi

  local src="delta_rt_src_$$" local_db="delta_rt_local_$$" dump_dir report_base dump preview_run apply_run
  dump_dir="$TMP_BASE/dumps"
  report_base="$TMP_BASE/reports"
  mkdir -p "$dump_dir" "$report_base"
  dump="$dump_dir/keep.dump"

  create_db "$src" || { skip "integration: could not create $src"; return 0; }
  create_db "$local_db" || { skip "integration: could not create $local_db"; return 0; }

  psql_db "$src" -f "$FIXTURES_DIR/minimal_schema.sql" -f "$FIXTURES_DIR/t01_identical.sql" >/dev/null || { fail 'integration: seed source DB'; return 1; }
  psql_db "$local_db" -f "$FIXTURES_DIR/minimal_schema.sql" -f "$FIXTURES_DIR/t01_identical.sql" >/dev/null || { fail 'integration: seed local DB'; return 1; }

  if (cd "$DATA_TOOL_DIR" && PG_BIN="$PG_BIN" PGDATABASE="$src" BACKUP_DIR="$dump_dir" DUMP="$dump" ./backup_extract_tables.sh >/dev/null); then
    pass 'integration: preserved-table backup dump created'
  else
    fail 'integration: preserved-table backup dump'
    return 1
  fi

  if (cd "$DATA_TOOL_DIR" && PG_BIN="$PG_BIN" PGDATABASE="$local_db" ./delta_restore_extract.sh --dump "$dump" --mode preview --report-dir "$report_base" >/dev/null); then
    preview_run="$(latest_run_dir "$report_base")"
    pass 'integration: preview completed'
  else
    fail 'integration: preview completed'
    return 1
  fi

  local pattern missing=false
  while read -r pattern; do
    [[ -n "$pattern" ]] || continue
    if ! grep -q "$pattern" "$preview_run/preview.txt"; then
      printf >&2 'missing preview pattern: %s\n' "$pattern"
      missing=true
    fi
  done < "$EXPECTED_DIR/t01_preview_patterns.txt"
  if [[ "$missing" = "false" ]]; then
    pass 'integration: preview report contains expected sections/classes'
  else
    fail 'integration: preview report expected patterns'
    return 1
  fi

  if (cd "$DATA_TOOL_DIR" && PG_BIN="$PG_BIN" PGDATABASE="$local_db" ./delta_restore_extract.sh --dump "$dump" --mode apply --selection-file "$preview_run/selection.conf" --report-dir "$report_base" --yes --keep-artifacts >/dev/null); then
    apply_run="$(latest_run_dir "$report_base")"
    pass 'integration: apply completed for identical dump'
  else
    fail 'integration: apply completed for identical dump'
    return 1
  fi

  if grep -q 'Apply summary' "$apply_run/apply_summary.txt" && grep -q 'Affected counts' "$apply_run/apply_summary.txt"; then
    pass 'integration: apply summary contains expected sections'
  else
    fail 'integration: apply summary expected sections'
    return 1
  fi
}

main() {
  require_file "$DATA_TOOL_DIR/delta_restore_extract.sh" || return 1
  require_file "$DATA_TOOL_DIR/scripts/restore/delta/10_functions.sql" || return 1
  require_file "$DATA_TOOL_DIR/scripts/restore/delta/rewrite_copy_targets.awk" || return 1

  run_static_checks || true
  run_sql_smoke || true
  run_optional_integration || true

  printf '\nSummary: %s passed, %s failed, %s skipped\n' "$pass_count" "$fail_count" "$skip_count"
  [[ "$fail_count" -eq 0 ]]
}

main "$@"
