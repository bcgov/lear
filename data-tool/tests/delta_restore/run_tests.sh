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
  static       Shell syntax plus guarded COPY-header and detail-alignment AWK paths.
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

path_mode() {
  local path="$1"
  if stat -f '%Lp' "$path" >/dev/null 2>&1; then
    stat -f '%Lp' "$path"
  else
    stat -c '%a' "$path"
  fi
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

  local delta_usage
  delta_usage="$(
    unset PG_BIN
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    usage
  )"
  if grep -q '^Environment:$' <<<"$delta_usage" \
     && grep -Fq 'PG_BIN=/path/to/postgresql/bin' <<<"$delta_usage" \
     && grep -Fq 'optional PostgreSQL client-tools directory; unset or empty uses PATH' <<<"$delta_usage" \
     && ! grep -Fq '/opt/homebrew/opt/postgresql@15/bin/' <<<"$delta_usage" \
     && grep -q 'LOCK_TIMEOUT_SECONDS=30' <<<"$delta_usage" \
     && grep -q '^After run-directory initialization, each invocation prints its artifact directory on exit:$' <<<"$delta_usage" \
     && grep -q 'Artifacts retained for inspection: <run-dir>' <<<"$delta_usage"; then
    pass 'delta restore help documents portable PG_BIN, lock timeout, and artifact handoff'
  else
    fail 'delta restore environment/artifact help contract'
    ok=false
  fi

  if (
    unset PG_BIN
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    [[ -z "$PG_BIN" ]]
    [[ "$(pg_tool psql)" = "psql" ]]
    [[ "$PSQL_BIN" = "psql" ]]
    [[ "$PG_RESTORE_BIN" = "pg_restore" ]]
  ) && (
    PG_BIN=""
    export PG_BIN
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    [[ -z "$PG_BIN" ]]
    [[ "$(pg_tool psql)" = "psql" ]]
    [[ "$PSQL_BIN" = "psql" ]]
    [[ "$PG_RESTORE_BIN" = "pg_restore" ]]
  ) && (
    PG_BIN="/custom/postgresql/bin/"
    export PG_BIN
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    [[ "$PG_BIN" = "/custom/postgresql/bin/" ]]
    [[ "$(pg_tool psql)" = "/custom/postgresql/bin/psql" ]]
    [[ "$PSQL_BIN" = "/custom/postgresql/bin/psql" ]]
    [[ "$PG_RESTORE_BIN" = "/custom/postgresql/bin/pg_restore" ]]
  ); then
    pass 'delta PG_BIN resolver handles unset, empty, and explicit directory states'
  else
    fail 'delta PG_BIN resolver behavior'
    ok=false
  fi

  local private_tmp
  private_tmp="$TMP_BASE/private_artifacts"
  if (
    umask 022
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    mkdir -p "$private_tmp/run"
    : > "$private_tmp/run/artifact.txt"
    [[ "$(path_mode "$private_tmp/run")" = "700" ]]
    [[ "$(path_mode "$private_tmp/run/artifact.txt")" = "600" ]]
  ); then
    pass 'delta restore artifacts default to private directory/file permissions'
  else
    fail 'delta restore private artifact permissions'
    ok=false
  fi

  local awk_tmp expected sidecar out err aligned expected_aligned canonical
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

  cat > "$awk_tmp/details.tsv" <<'TSV'
id	name	note
1	Ada	short
22	Longer	1234567890
# TRUNCATED at 2 rows
TSV
  cat > "$awk_tmp/details.expected.txt" <<'TXT'
id  name    note
--  ------  --------
1   Ada     short
22  Longer  1234567…
# TRUNCATED at 2 rows
TXT
  aligned="$awk_tmp/details.txt"
  expected_aligned="$awk_tmp/details.expected.txt"
  canonical="$awk_tmp/details.canonical.tsv"
  cp "$awk_tmp/details.tsv" "$canonical"
  if awk -v max_width=8 -f "$DATA_TOOL_DIR/scripts/restore/delta/align_details.awk" \
       "$awk_tmp/details.tsv" "$awk_tmp/details.tsv" > "$aligned" \
     && cmp -s "$expected_aligned" "$aligned" \
     && awk -v max_width=8 -f "$DATA_TOOL_DIR/scripts/restore/delta/align_details.awk" \
          "$awk_tmp/details.tsv" "$awk_tmp/details.tsv" | cmp -s "$expected_aligned" -; then
    pass 'detail aligner pads columns, clips cells, preserves sentinel, and is deterministic'
  else
    fail 'detail aligner formatting contract'
    ok=false
  fi

  : > "$awk_tmp/empty.tsv"
  if awk -f "$DATA_TOOL_DIR/scripts/restore/delta/align_details.awk" \
       "$awk_tmp/empty.tsv" "$awk_tmp/empty.tsv" > "$aligned" \
     && [[ ! -s "$aligned" ]]; then
    pass 'detail aligner produces no output for empty input'
  else
    fail 'detail aligner empty-input contract'
    ok=false
  fi

  if (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    parse_args --mode validate --no-aligned-details --align-width 3 --manifest-default none
    [[ "$MODE" = "validate" ]]
    [[ "$ALIGN_DETAILS" = "false" && "$ALIGN_WIDTH" = "6" ]]
    [[ "$MANIFEST_DEFAULT" = "none" ]]
  ); then
    pass 'validate mode, aligned-detail, and manifest-default CLI controls parse valid values'
  else
    fail 'validate mode, aligned-detail, or manifest-default CLI control parsing'
    ok=false
  fi

  if (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    [[ "$SELECTOR_SUGGESTION_LIMIT" = "50" ]]
    parse_args --selector-suggestion-limit 0
    [[ "$SELECTOR_SUGGESTION_LIMIT" = "0" ]]
    parse_args --selector-suggestion-limit 37
    [[ "$SELECTOR_SUGGESTION_LIMIT" = "37" ]]
    parse_args --selector-suggestion-limit 00007
    [[ "$SELECTOR_SUGGESTION_LIMIT" = "7" ]]
    parse_args --selector-suggestion-limit 100000
    [[ "$SELECTOR_SUGGESTION_LIMIT" = "100000" ]]
  ); then
    pass 'selector-suggestion-limit accepts default, zero, custom, canonical, and maximum values'
  else
    fail 'selector-suggestion-limit valid-value parsing or canonicalization'
    ok=false
  fi

  selector_limit_rejections=true
  for invalid_limit in -1 text +1 1.5 100001 999999999999999999999999999999; do
    if (
      DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
      parse_args --selector-suggestion-limit "$invalid_limit"
    ) >/dev/null 2>&1; then
      selector_limit_rejections=false
    fi
  done
  if (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    parse_args --selector-suggestion-limit
  ) >/dev/null 2>&1; then
    selector_limit_rejections=false
  fi
  if [[ "$selector_limit_rejections" = "true" ]]; then
    pass 'selector-suggestion-limit rejects negative, malformed, above-cap, huge, and missing values'
  else
    fail 'selector-suggestion-limit accepted an invalid value'
    ok=false
  fi

  if (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    help_text="$(usage)"
    [[ "$help_text" = *'--selector-suggestion-limit <n>'* ]]
    [[ "$help_text" = *'exact manifest suggestions per table/class; default: 50'* ]]
    [[ "$help_text" = *'0 disables exact suggestions; maximum: 100000'* ]]
  ); then
    pass 'selector-suggestion-limit help documents scope, default, zero, and maximum'
  else
    fail 'selector-suggestion-limit help contract'
    ok=false
  fi

  (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    parse_args --mode verify
  ) >/dev/null 2>&1
  if [[ "$?" -ne 0 ]]; then
    pass 'mode CLI rejects unsupported values while accepting validate'
  else
    fail 'mode CLI accepted an unsupported value'
    ok=false
  fi
  (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    parse_args --align-width 0
  ) >/dev/null 2>&1
  if [[ "$?" -ne 0 ]]; then
    pass 'aligned-detail CLI rejects a zero width'
  else
    fail 'aligned-detail CLI accepted a zero width'
    ok=false
  fi
  (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    parse_args --manifest-default changed
  ) >/dev/null 2>&1
  if [[ "$?" -ne 0 ]]; then
    pass 'manifest-default CLI rejects unsupported defaults'
  else
    fail 'manifest-default CLI accepted an unsupported default'
    ok=false
  fi
  printf 'resident dump fixture\n' > "$awk_tmp/resident.dump"
  if (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    RUN_DIR="$awk_tmp"
    DUMP="$awk_tmp/resident.dump"
    DUMP_SHA256=""
    compute_dump_sha
    [[ -n "$DUMP_SHA256" ]]
    [[ "$DUMP_SHA256" = "$(sha256_file "$DUMP")" ]]
    [[ "$(cat "$RUN_DIR/dump.sha256")" = "$DUMP_SHA256" ]]
  ); then
    pass 'dump sha helper safely sets the shared hash and writes its binding artifact'
  else
    fail 'dump sha helper shared-state contract'
    ok=false
  fi

  if (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    apply_body="$(declare -f run_apply_mode)"
    [[ "$apply_body" = *'verify_dump_and_manifest'* ]]
    [[ "$apply_body" = *'filter_toc'* ]]
    [[ "$apply_body" = *'install_control_schemas'* ]]
    [[ "$apply_body" = *'stream_stage_data'* ]]
    [[ "$apply_body" = *'run_preview_classification'* ]]
    [[ "$apply_body" = *'prepare_apply_selection'* ]]
  ); then
    pass 'apply retains full dump verification, restaging, and reclassification posture'
  else
    fail 'apply full-restage posture changed'
    ok=false
  fi

  if (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    validate_body="$(declare -f run_validate_mode)"
    [[ "$validate_body" = *'verify_resident_run'* ]]
    [[ "$validate_body" = *'load_preserved_config'* ]]
    [[ "$validate_body" = *'select_tables'* ]]
    [[ "$validate_body" = *'prepare_apply_selection'* ]]
    [[ "$validate_body" != *'filter_toc'* ]]
    [[ "$validate_body" != *'install_control_schemas'* ]]
    [[ "$validate_body" != *'stream_stage_data'* ]]
    [[ "$validate_body" != *'run_preview_classification'* ]]
  ); then
    pass 'validate reuses resident selection preparation without staging or classification'
  else
    fail 'validate resident-only dispatch contract'
    ok=false
  fi

  if (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    RUN_DIR="$awk_tmp"
    MODE="preview"
    DUMP="/tmp/manifest-default.dump"
    DUMP_SHA256="manifest-default-sha"
    MANIFEST_DEFAULT="none"
    psql_file() { :; return 0; }
    record_metadata
    grep -Fq "('manifest_default', 'none')" "$RUN_DIR/metadata.sql"
    grep -Fq "('selector_suggestion_limit', '50')" "$RUN_DIR/metadata.sql"
  ); then
    pass 'manifest and default selector limits are persisted into run metadata for SQL rendering'
  else
    fail 'manifest-default or selector-limit run metadata plumbing'
    ok=false
  fi

  if (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    parse_args --selector-suggestion-limit 00000
    RUN_DIR="$awk_tmp"
    MODE="preview"
    DUMP="/tmp/selector-limit.dump"
    DUMP_SHA256="selector-limit-sha"
    psql_file() { :; return 0; }
    record_metadata
    grep -Fq "('selector_suggestion_limit', '0')" "$RUN_DIR/metadata.sql"
  ); then
    pass 'canonical custom selector limit is persisted into run metadata'
  else
    fail 'custom selector-limit metadata plumbing'
    ok=false
  fi

  if (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    manifest_body="$(declare -f write_selection_manifest)"
    [[ "$manifest_body" = *'SELECT * FROM delta_ctl.render_selection_manifest();'* ]]
    [[ "$manifest_body" != *'$SELECTOR_SUGGESTION_LIMIT'* ]]
  ); then
    pass 'selection manifest keeps the zero-argument SQL renderer invocation'
  else
    fail 'selection manifest renderer invocation changed signature or gained shell interpolation'
    ok=false
  fi

  if (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    RUN_DIR="$awk_tmp"
    ALIGN_DETAILS="true"
    ALIGN_WIDTH="8"
    write_aligned_detail "$awk_tmp/details.tsv" "10" "NEW"
    cmp -s "$canonical" "$awk_tmp/details.tsv"
    grep -q '^# rendered 2 of 10 NEW rows — TRUNCATED$' "$awk_tmp/details.txt"
  ); then
    pass 'aligned companion preserves TSV bytes and appends rendered/total footer'
  else
    fail 'aligned companion TSV preservation and footer semantics'
    ok=false
  fi

  rm -f "$awk_tmp/details.txt"
  if (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    RUN_DIR="$awk_tmp"
    ALIGN_DETAILS="false"
    write_aligned_detail "$awk_tmp/details.tsv" "10" "NEW"
    [[ ! -e "$awk_tmp/details.txt" ]]
  ); then
    pass 'aligned companion generation can be disabled'
  else
    fail 'aligned companion disable control'
    ok=false
  fi

  local parser_tmp="$TMP_BASE/selection_parser"
  mkdir -p "$parser_tmp"
  printf 'bad_emails\nbar_corps\n' > "$parser_tmp/all_conf_tables.txt"
  cat > "$parser_tmp/happy.conf" <<'CONF'
# delta-selection v2
# dump_sha256=abc123
# staged bad_emails=3 bar_corps=2
# Operator cookbook (all examples remain comments)
#   Class override: [<table>] include=new,changed
#   Disable a table: [<table>] include=
# [bad_emails] 51 NEW rows: review details/bad_emails.new.tsv; supported selectors: id:
[*] include=new,changed
[bad_emails] new.rows include=id:1-3,8,9007199254740993,9223372036854775807
[bar_corps] changed.rows exclude=corp:BC0000001,BC\N
CONF
  if (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    RUN_DIR="$parser_tmp"; SELECTION_FILE="$parser_tmp/happy.conf"
    build_selection_input
    grep -q $'bad_emails\tNEW\tinclude\tid\t1\t3\t\\N\tt' "$RUN_DIR/row_selection_input.tsv"
    grep -q $'bad_emails\tNEW\tinclude\tid\t9223372036854775807\t9223372036854775807' "$RUN_DIR/row_selection_input.tsv"
    grep -q $'bar_corps\tCHANGED\texclude\tcorp\t\\N\t\\N\tBC0000001' "$RUN_DIR/row_selection_input.tsv"
    awk -F '\t' '$4 == "corp" && $7 == "BC\\\\N" { found=1 } END { exit !found }' "$RUN_DIR/row_selection_input.tsv"
    grep -q $'dump_sha256\tabc123' "$RUN_DIR/selection_header.tsv"
    [[ "$(wc -l < "$RUN_DIR/selection_header.tsv" | tr -d ' ')" = "3" ]]
    ! grep -q '<table>\|51 NEW rows' "$RUN_DIR/selection_input.tsv" "$RUN_DIR/row_selection_input.tsv"
  ); then
    pass 'selection parser accepts v2 selectors/bindings and ignores generated cookbook comments'
  else
    fail 'selection parser v2 happy path and cookbook comment compatibility'
    ok=false
  fi

  printf 'bad_emails\n' > "$parser_tmp/requested_tables.txt"
  printf 'bad_emails\tNEW\n' > "$parser_tmp/scoped.expected.tsv"
  if (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    RUN_DIR="$parser_tmp"
    SELECTION_FILE="$parser_tmp/happy.conf"
    TABLES_ARG="bad_emails"
    INCLUDE_CLASSES="new,changed"
    EXCLUDE_CLASSES="changed"
    build_selection_input
    cmp -s "$RUN_DIR/scoped.expected.tsv" "$RUN_DIR/selection_input.tsv"
  ); then
    pass 'selection file candidates are bounded by explicit table/include/exclude scope'
  else
    fail 'selection file table/class scope ceiling'
    ok=false
  fi

  cat > "$parser_tmp/duplicate_sha.conf" <<'CONF'
# dump_sha256=abc123
# dump_sha256=abc123
[*] include=new
CONF
  cat > "$parser_tmp/duplicate_staged.conf" <<'CONF'
# staged bad_emails=3
# staged bar_corps=2 bad_emails=3
[*] include=new
CONF
  cat > "$parser_tmp/nondecimal_staged.conf" <<'CONF'
# staged bad_emails=three
[*] include=new
CONF
  local bad_header expected_error parser_status
  for bad_header in duplicate_sha duplicate_staged nondecimal_staged; do
    case "$bad_header" in
      duplicate_sha) expected_error='duplicate dump_sha256 header' ;;
      duplicate_staged) expected_error='duplicate staged-count header' ;;
      nondecimal_staged) expected_error='staged count must be decimal' ;;
      *) expected_error='unexpected parser fixture' ;;
    esac
    (
      DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
      RUN_DIR="$parser_tmp"; SELECTION_FILE="$parser_tmp/$bad_header.conf"
      build_selection_input
    ) >/dev/null 2>&1
    parser_status=$?
    if [[ "$parser_status" -eq 4 ]]; then
      pass "selection parser rejects $expected_error with exit 4"
    else
      fail "selection parser $expected_error expected exit 4, got $parser_status"
      ok=false
    fi
  done

  cat > "$parser_tmp/inverted.conf" <<'CONF'
[*] include=new
[bad_emails] new.rows include=id:9-3
CONF
  if (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    RUN_DIR="$parser_tmp"; SELECTION_FILE="$parser_tmp/inverted.conf"
    build_selection_input
  ) >/dev/null 2>&1; then
    fail 'selection parser rejects inverted ranges'
    ok=false
  else
    pass 'selection parser rejects inverted ranges'
  fi

  cat > "$parser_tmp/bad_kind.conf" <<'CONF'
[*] include=new
[bad_emails] new.rows include=pk:1
CONF
  if (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    RUN_DIR="$parser_tmp"; SELECTION_FILE="$parser_tmp/bad_kind.conf"
    build_selection_input
  ) >/dev/null 2>&1; then
    fail 'selection parser rejects unsupported selector kinds'
    ok=false
  else
    pass 'selection parser rejects unsupported selector kinds'
  fi

  cat > "$parser_tmp/bigint_overflow.conf" <<'CONF'
[*] include=new
[bad_emails] new.rows include=id:9223372036854775808
CONF
  if (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    RUN_DIR="$parser_tmp"; SELECTION_FILE="$parser_tmp/bigint_overflow.conf"
    build_selection_input
  ) >/dev/null 2>&1; then
    fail 'selection parser rejects integers above bigint maximum'
    ok=false
  else
    pass 'selection parser rejects integers above bigint maximum'
  fi

  cat > "$parser_tmp/v1.conf" <<'CONF'
[*] include=new,changed
[bar_corps] include=
CONF
  if (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    RUN_DIR="$parser_tmp"; SELECTION_FILE="$parser_tmp/v1.conf"
    build_selection_input
    [[ ! -s "$RUN_DIR/row_selection_input.tsv" ]]
    grep -q $'bad_emails\tNEW' "$RUN_DIR/selection_input.tsv"
  ); then
    pass 'selection parser preserves class-only v1 compatibility'
  else
    fail 'selection parser class-only v1 compatibility'
    ok=false
  fi

  if (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    RUN_DIR="$parser_tmp"; DUMP_SHA256="current"
    printf 'bad_emails\tNEW\tinclude\tid\t1\t1\t\\N\tf\t1\n' > "$RUN_DIR/row_selection_input.tsv"
    printf 'dump_sha256\tdifferent\n' > "$RUN_DIR/selection_header.tsv"
    verify_selection_binding
  ) >/dev/null 2>&1; then
    fail 'selection binding rejects a different dump hash'
    ok=false
  else
    pass 'selection binding rejects a different dump hash'
  fi

  if (
    DELTA_RESTORE_SOURCE_ONLY=true source "$DATA_TOOL_DIR/delta_restore_extract.sh"
    RUN_DIR="$parser_tmp"; DUMP_SHA256="current"
    printf 'bar_corps\tNEW\tinclude\trow\t1\t1\t\\N\tf\t1\n' > "$RUN_DIR/row_selection_input.tsv"
    printf 'dump_sha256\tcurrent\nstaged\tbar_corps\t9\n' > "$RUN_DIR/selection_header.tsv"
    printf 'bar_corps\tSTAGED\t8\n' > "$RUN_DIR/stage_counts.tsv"
    verify_selection_binding
  ) >/dev/null 2>&1; then
    fail 'row selector binding rejects a changed staged count'
    ok=false
  else
    pass 'row selector binding rejects a changed staged count'
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
       -f "$EXPECTED_DIR/t11_nk_hash_join_perf_assert.sql" \
       -f "$FIXTURES_DIR/t12_row_selection.sql" \
       -f "$EXPECTED_DIR/t12_row_selection_assert.sql" \
       -f "$FIXTURES_DIR/t13_selector_diagnostics.sql" \
       -f "$EXPECTED_DIR/t13_selector_diagnostics_assert.sql" \
       -f "$FIXTURES_DIR/t14_parent_dependency_rows.sql" \
       -f "$EXPECTED_DIR/t14_parent_dependency_rows_assert.sql" \
       -f "$FIXTURES_DIR/t15_details.sql" \
       -f "$EXPECTED_DIR/t15_details_assert.sql" \
       -f "$FIXTURES_DIR/t16_selection_manifest.sql" \
       -f "$EXPECTED_DIR/t16_selection_manifest_assert.sql" \
       -f "$FIXTURES_DIR/t17_selection_cookbook.sql" \
       -f "$EXPECTED_DIR/t17_selection_cookbook_assert.sql" >/dev/null; then
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
  local scope_dump scope_preview hint_dir hint_only_corps preview_stdout validate_command apply_command
  local hint_validate_stdout hint_validate_run hint_validate_status hint_validate_counts
  local hint_apply_stdout hint_apply_run hint_apply_status hint_apply_counts
  dump_dir="$TMP_BASE/dumps"
  report_base="$TMP_BASE/reports"
  hint_dir="$TMP_BASE/preview-hint"
  hint_only_corps="$hint_dir/only-corps.txt"
  preview_stdout="$hint_dir/preview.out"
  hint_validate_stdout="$hint_dir/validate.out"
  hint_validate_counts="$hint_dir/validate-selected-counts.tsv"
  hint_apply_stdout="$hint_dir/apply.out"
  hint_apply_counts="$hint_dir/apply-selected-counts.tsv"
  mkdir -p "$dump_dir" "$report_base" "$hint_dir"
  printf 'BC0000001\n' > "$hint_only_corps"
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

  if (cd "$DATA_TOOL_DIR" && PG_BIN="$PG_BIN" PGDATABASE="$local_db" ./delta_restore_extract.sh \
      --dump "$dump" --mode preview --report-dir "$report_base" >/dev/null); then
    preview_run="$(latest_run_dir "$report_base")"
    pass 'integration: preview completed'
  else
    fail 'integration: preview completed'
    return 1
  fi

  if [[ "$(path_mode "$preview_run")" = "700" ]] \
     && [[ "$(path_mode "$preview_run/preview.txt")" = "600" ]] \
     && [[ "$(path_mode "$preview_run/selection.conf")" = "600" ]] \
     && [[ "$(path_mode "$preview_run/selection_cookbook.txt")" = "600" ]] \
     && grep -q '^# OPERATOR COOKBOOK$' "$preview_run/selection_cookbook.txt" \
     && grep -q 'selection_cookbook.txt (this run dir)' "$preview_run/selection.conf"; then
    pass 'integration: preview selection artifacts are private and cookbook is split from manifest'
  else
    fail 'integration: preview artifact permissions'
    return 1
  fi

  local pattern missing=false
  while read -r pattern; do
    [[ -n "$pattern" ]] || continue
    if ! grep -q -- "$pattern" "$preview_run/preview.txt"; then
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

  if grep -q 'Apply summary' "$apply_run/apply_summary.txt" \
     && grep -q 'Affected counts' "$apply_run/apply_summary.txt" \
     && [[ -f "$apply_run/selection_cookbook.txt" ]] \
     && grep -q '^# OPERATOR COOKBOOK$' "$apply_run/selection_cookbook.txt"; then
    pass 'integration: apply summary and selection cookbook contain expected sections'
  else
    fail 'integration: apply summary or selection cookbook expected sections'
    return 1
  fi

  scope_dump="$dump_dir/scoped-selection.dump"
  psql_db "$src" -c "UPDATE bad_emails SET notes = 'source-changed' WHERE id = 1;
    INSERT INTO bad_emails(id, email, notes) VALUES (201, 'scope-in@example.test', 'inside');
    INSERT INTO excluded_emails(email, notes) VALUES ('scope-out@example.test', 'outside');" >/dev/null || {
      fail 'integration: seed scoped selectable rows'; return 1;
    }
  if (cd "$DATA_TOOL_DIR" && PG_BIN="$PG_BIN" PGDATABASE="$src" BACKUP_DIR="$dump_dir" DUMP="$scope_dump" ./backup_extract_tables.sh >/dev/null); then
    pass 'integration: scoped-selection dump created'
  else
    fail 'integration: scoped-selection dump creation'
    return 1
  fi
  if (cd "$hint_dir" && PG_BIN="$PG_BIN" PGDATABASE="$local_db" "$DATA_TOOL_DIR/delta_restore_extract.sh" \
      --dump "$scope_dump" --mode preview --tables bad_emails \
      --include-classes new,changed --exclude-classes changed \
      --only-corps "$hint_only_corps" --report-dir "$report_base" > "$preview_stdout" 2>&1); then
    scope_preview="$(latest_run_dir "$report_base")"
    pass 'integration: scoped preview completed with selectable rows inside and outside scope'
  else
    fail 'integration: scoped preview'
    return 1
  fi

  cp "$scope_preview/selection.conf" "$hint_dir/my_selection.conf"
  validate_command="$(sed -n 's/^  3[.] To validate: //p' "$preview_stdout" | tail -n 1)"
  (cd "$hint_dir" && PG_BIN="$PG_BIN" PGDATABASE="$local_db" bash -c "$validate_command" \
    > "$hint_validate_stdout" 2>&1)
  hint_validate_status=$?
  hint_validate_run="$(sed -n 's/^Artifacts: //p' "$hint_validate_stdout" | tail -n 1)"
  if [[ -f "$hint_validate_run/selected_counts.tsv" ]]; then
    cp "$hint_validate_run/selected_counts.tsv" "$hint_validate_counts"
  fi
  case "$hint_validate_run" in
    "$DATA_TOOL_DIR/scripts/generated/delta_restore/"*) rm -rf -- "$hint_validate_run" ;;
    *) ;;
  esac
  if [[ "$hint_validate_status" -eq 0 ]] \
     && grep -q '^  3[.] To validate:' "$preview_stdout" \
     && grep -Fq -- '--tables bad_emails' <<<"$validate_command" \
     && grep -Fq -- '--include-classes new\,changed' <<<"$validate_command" \
     && grep -Fq -- '--exclude-classes changed' <<<"$validate_command" \
     && grep -Fq -- "--only-corps $hint_only_corps" <<<"$validate_command" \
     && grep -q 'Selection is valid' "$hint_validate_stdout" \
     && awk -F '\t' 'NR == 1 && $1 == "bad_emails" && $2 == "NEW" && $3 == "1" { ok=1 }
          END { exit !(NR == 1 && ok) }' "$hint_validate_counts"; then
    pass 'integration: printed validate command enforces table/class scope in actual selected counts'
  else
    fail "integration: printed scoped validate expected one bad_emails NEW row, got status $hint_validate_status"
    return 1
  fi

  apply_command="$(sed -n 's/^To apply: //p' "$hint_validate_stdout" | tail -n 1)"
  (cd "$hint_dir" && PG_BIN="$PG_BIN" PGDATABASE="$local_db" bash -c "$apply_command" \
    > "$hint_apply_stdout" 2>&1)
  hint_apply_status=$?
  hint_apply_run="$(sed -n 's/^Artifacts: //p' "$hint_apply_stdout" | tail -n 1)"
  if [[ -f "$hint_apply_run/selected_counts.tsv" ]]; then
    cp "$hint_apply_run/selected_counts.tsv" "$hint_apply_counts"
  fi
  if [[ -f "$hint_apply_run/apply_summary.txt" ]]; then
    cp "$hint_apply_run/apply_summary.txt" "$hint_dir/scoped-apply-summary.txt"
  fi
  case "$hint_apply_run" in
    "$DATA_TOOL_DIR/scripts/generated/delta_restore/"*) rm -rf -- "$hint_apply_run" ;;
    *) ;;
  esac
  if [[ "$hint_apply_status" -eq 0 ]] \
     && grep -Fq -- '--tables bad_emails' <<<"$apply_command" \
     && grep -Fq -- '--include-classes new\,changed' <<<"$apply_command" \
     && grep -Fq -- '--exclude-classes changed' <<<"$apply_command" \
     && grep -Fq -- "--only-corps $hint_only_corps" <<<"$apply_command" \
     && awk -F '\t' 'NR == 1 && $1 == "bad_emails" && $2 == "NEW" && $3 == "1" { ok=1 }
          END { exit !(NR == 1 && ok) }' "$hint_apply_counts" \
     && [[ "$(psql_db "$local_db" -qAt -c "SELECT count(*) FROM bad_emails WHERE id = 201")" = "1" ]] \
     && [[ "$(psql_db "$local_db" -qAt -c "SELECT notes FROM bad_emails WHERE id = 1")" = "seed" ]] \
     && [[ "$(psql_db "$local_db" -qAt -c "SELECT count(*) FROM excluded_emails WHERE email = 'scope-out@example.test'")" = "0" ]] \
     && grep -Eq 'bad_emails[[:space:]]+NEW[[:space:]]+INSERT[[:space:]]+1[[:space:]]+1' "$hint_dir/scoped-apply-summary.txt"; then
    pass 'integration: printed apply command cannot select or modify rows outside explicit table/class scope'
  else
    fail "integration: printed scoped apply expected only one bad_emails NEW row, got status $hint_apply_status"
    return 1
  fi

  psql_db "$local_db" -c "UPDATE bad_emails SET notes = 'source-changed' WHERE id = 1;
    INSERT INTO excluded_emails(email, notes) VALUES ('scope-out@example.test', 'outside');" >/dev/null || {
      fail 'integration: synchronize rows after scoped safety assertions'; return 1;
    }

  local row_dump="$dump_dir/row-selection.dump" row_preview row_validate bad_validate_run row_apply
  local row_selection bad_selector_selection bad_selection validate_status mismatch_status
  psql_db "$src" -c "INSERT INTO bad_emails(id, email, notes) VALUES
    (101, 'row101@example.test', 'one'),
    (102, 'row102@example.test', 'two'),
    (103, 'row103@example.test', 'three');" >/dev/null || {
      fail 'integration: seed row-selection source rows'; return 1;
    }
  if (cd "$DATA_TOOL_DIR" && PG_BIN="$PG_BIN" PGDATABASE="$src" BACKUP_DIR="$dump_dir" DUMP="$row_dump" ./backup_extract_tables.sh >/dev/null); then
    pass 'integration: row-selection dump created'
  else
    fail 'integration: row-selection dump creation'
    return 1
  fi
  if (cd "$DATA_TOOL_DIR" && PG_BIN="$PG_BIN" PGDATABASE="$local_db" ./delta_restore_extract.sh --dump "$row_dump" --mode preview --report-dir "$report_base" --details-limit 2 >/dev/null); then
    row_preview="$(latest_run_dir "$report_base")"
    pass 'integration: row-selection preview completed'
  else
    fail 'integration: row-selection preview'
    return 1
  fi
  if [[ -f "$row_preview/details/bad_emails.new.tsv" ]] &&
     grep -q 'row101@example.test' "$row_preview/details/bad_emails.new.tsv"; then
    pass 'integration: NEW detail artifact contains staged row values'
  else
    fail 'integration: NEW detail artifact'
    return 1
  fi
  if [[ -f "$row_preview/details/bad_emails.new.txt" ]] \
     && [[ "$(path_mode "$row_preview/details/bad_emails.new.txt")" = "600" ]] \
     && grep -q '^# rendered 2 of 3 NEW rows — TRUNCATED$' "$row_preview/details/bad_emails.new.txt" \
     && grep -q '^# TRUNCATED at 2 rows$' "$row_preview/details/bad_emails.new.tsv" \
     && grep -Fq -- '- details/bad_emails.new.tsv — 2 of 3 NEW rows (TRUNCATED) · aligned: details/bad_emails.new.txt' "$row_preview/preview.txt"; then
    pass 'integration: truncated aligned NEW detail has private mode, footer, and preview counts'
  else
    fail 'integration: truncated aligned NEW detail and preview count enrichment'
    return 1
  fi

  row_selection="$TMP_BASE/row-selection.conf"
  cp "$row_preview/selection.conf" "$row_selection"
  printf '\n[bad_emails] new.rows include=id:101-102\n' >> "$row_selection"

  (cd "$DATA_TOOL_DIR" && PG_BIN="$PG_BIN" PGDATABASE="$local_db" ./delta_restore_extract.sh \
    --dump "$row_dump" --mode validate --selection-file "$row_selection" \
    --report-dir "$report_base" > "$TMP_BASE/validate.out" 2>&1)
  validate_status=$?
  row_validate="$(latest_run_dir "$report_base")"
  if [[ "$validate_status" -eq 0 ]] \
     && grep -q 'Selection is valid' "$TMP_BASE/validate.out" \
     && grep -q $'bad_emails\tNEW\t2\t' "$row_validate/selected_counts.tsv"; then
    pass 'integration: resident selection validate exits 0 with expected selected counts'
  else
    fail "integration: resident selection validate expected exit 0, got $validate_status"
    return 1
  fi
  if [[ -s "$row_validate/stage_counts.tsv" ]] \
     && [[ ! -e "$row_validate/toc.list" ]] \
     && [[ ! -e "$row_validate/stage_counts.sql" ]] \
     && [[ ! -e "$row_validate/create_stage_shells.sql" ]] \
     && [[ ! -e "$row_validate/preview_classification.sql" ]]; then
    pass 'integration: validate regenerates staged counts without TOC read, staging, or classification'
  else
    fail 'integration: validate performed or failed to exclude restaging work'
    return 1
  fi

  bad_selector_selection="$TMP_BASE/row-selection-invalid-selector.conf"
  cp "$row_selection" "$bad_selector_selection"
  printf '[bad_emails] new.rows include=id:999999\n' >> "$bad_selector_selection"
  (cd "$DATA_TOOL_DIR" && PG_BIN="$PG_BIN" PGDATABASE="$local_db" ./delta_restore_extract.sh \
    --dump "$row_dump" --mode validate --selection-file "$bad_selector_selection" \
    --report-dir "$report_base" > "$TMP_BASE/validate-invalid.out" 2>&1)
  validate_status=$?
  bad_validate_run="$(latest_run_dir "$report_base")"
  if [[ "$validate_status" -eq 4 ]] \
     && grep -Fq $'bad_emails\tNEW\tinclude\tid\t999999\t' "$bad_validate_run/selection_diagnostics.tsv" \
     && grep -Fq $'\tNO_MATCH' "$bad_validate_run/selection_diagnostics.tsv" \
     && [[ ! -e "$bad_validate_run/toc.list" ]] \
     && [[ ! -e "$bad_validate_run/preview_classification.sql" ]]; then
    pass 'integration: invalid resident selector exits 4 with diagnostics and no restaging'
  else
    fail "integration: invalid resident selector expected exit 4, got $validate_status"
    return 1
  fi

  if (cd "$DATA_TOOL_DIR" && PG_BIN="$PG_BIN" PGDATABASE="$local_db" ./delta_restore_extract.sh --dump "$row_dump" --mode apply --selection-file "$row_selection" --report-dir "$report_base" --yes --keep-artifacts >/dev/null); then
    row_apply="$(latest_run_dir "$report_base")"
    pass 'integration: row-selector apply completed'
  else
    fail 'integration: row-selector apply'
    return 1
  fi
  if [[ "$(psql_db "$local_db" -qAt -c "SELECT count(*) FROM bad_emails WHERE id IN (101,102)")" = "2" ]] &&
     [[ "$(psql_db "$local_db" -qAt -c "SELECT count(*) FROM bad_emails WHERE id = 103")" = "0" ]] &&
     grep -Eq 'bad_emails[[:space:]]+NEW[[:space:]]+INSERT[[:space:]]+2[[:space:]]+2' "$row_apply/apply_summary.txt"; then
    pass 'integration: row selectors applied 2 rows and skipped 1 with expected=affected'
  else
    fail 'integration: row-selector applied/skipped row assertions'
    return 1
  fi

  bad_selection="$TMP_BASE/row-selection-bad-sha.conf"
  sed 's/^# dump_sha256=.*/# dump_sha256=0000/' "$row_selection" > "$bad_selection"
  (cd "$DATA_TOOL_DIR" && PG_BIN="$PG_BIN" PGDATABASE="$local_db" ./delta_restore_extract.sh --dump "$row_dump" --mode apply --selection-file "$bad_selection" --report-dir "$report_base" --yes --keep-artifacts >/dev/null 2>&1)
  mismatch_status=$?
  if [[ "$mismatch_status" -eq 4 ]]; then
    pass 'integration: row-selector dump hash mismatch exits 4'
  else
    fail "integration: row-selector hash mismatch expected exit 4, got $mismatch_status"
    return 1
  fi
}

main() {
  require_file "$DATA_TOOL_DIR/delta_restore_extract.sh" || return 1
  require_file "$DATA_TOOL_DIR/scripts/restore/delta/10_functions.sql" || return 1
  require_file "$DATA_TOOL_DIR/scripts/restore/delta/rewrite_copy_targets.awk" || return 1
  require_file "$DATA_TOOL_DIR/scripts/restore/delta/align_details.awk" || return 1

  run_static_checks || true
  run_sql_smoke || true
  run_optional_integration || true

  printf '\nSummary: %s passed, %s failed, %s skipped\n' "$pass_count" "$fail_count" "$skip_count"
  [[ "$fail_count" -eq 0 ]]
}

main "$@"
