#!/usr/bin/env bash
# delta_restore_extract.sh
#
# Delta restore pipeline for preserved-table preview/apply runs.
# Stages a preserved-table dump, classifies rows, writes preview artifacts, and
# optionally applies selected NEW/CHANGED rows.

set -euo pipefail
umask 077

##############################################################################
# CONNECTION DEFAULTS
##############################################################################

PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"
PGDATABASE="${PGDATABASE:-colin-mig-corps-test}"
# Optional PostgreSQL client binary directory. Leave empty to use PATH.
# Example: PG_BIN=/path/to/postgresql/bin ./delta_restore_extract.sh
PG_BIN="${PG_BIN:-}"

##############################################################################
# PATHS / DEFAULTS
##############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRESERVED_TABLES_CONF="$SCRIPT_DIR/scripts/restore/preserved_tables.conf"
DELTA_DIR="$SCRIPT_DIR/scripts/restore/delta"
INSTALL_SQL="$DELTA_DIR/00_install.sql"
FUNCTIONS_SQL="$DELTA_DIR/10_functions.sql"
SESSION_BEGIN_SQL="$DELTA_DIR/20_session_begin.sql"
SESSION_END_SQL="$DELTA_DIR/21_session_end.sql"
REWRITE_AWK="$DELTA_DIR/rewrite_copy_targets.awk"
ALIGN_DETAILS_AWK="$DELTA_DIR/align_details.awk"
REPAIR_SEQUENCES_SQL="$SCRIPT_DIR/scripts/restore/repair_sequences.sql"
ACQUIRE_LOCK_SQL="$SCRIPT_DIR/scripts/subset/subset_pg_acquire_advisory_lock.sql"
RELEASE_LOCK_SQL="$SCRIPT_DIR/scripts/subset/subset_pg_release_advisory_lock.sql"
DEFAULT_REPORT_BASE="$SCRIPT_DIR/scripts/generated/delta_restore"

DUMP="${DUMP:-}"
MODE="preview"
TABLES_ARG="all"
INCLUDE_CLASSES=""
EXCLUDE_CLASSES=""
SELECTION_FILE=""
ONLY_CORPS_FILE=""
SAMPLE_SIZE="20"
DETAILS_LIMIT="10000"
SELECTOR_SUGGESTION_LIMIT="50"
SELECTOR_SUGGESTION_LIMIT_MAX="100000"
ALIGN_DETAILS="true"
ALIGN_WIDTH="40"
MANIFEST_DEFAULT="new,changed"
DUMP_SHA256=""
REPORT_BASE="$DEFAULT_REPORT_BASE"
KEEP_ARTIFACTS="false"
YES="false"
CLEANUP="false"
LOCK_TIMEOUT_SECONDS="${LOCK_TIMEOUT_SECONDS:-30}"

RUN_DIR=""
LOCK_FIFO=""
LOCK_PID=""
LOCK_ACQUIRED="false"

##############################################################################
# HELPERS
##############################################################################

die_with_code() {
  local code="$1"
  shift
  printf >&2 "error: %s\n" "$*"
  exit "$code"
}

die() { die_with_code 1 "$@"; }
die2() { die_with_code 2 "$@"; }
die3() { die_with_code 3 "$@"; }
die4() { die_with_code 4 "$@"; }
die5() { die_with_code 5 "$@"; }

usage() {
  cat <<'USAGE'
Usage:
  delta_restore_extract.sh --dump <path> [--mode preview|apply|validate] [options]
  delta_restore_extract.sh --cleanup

Options parsed now:
  --dump <path>                 pg_dump -Fc archive to stage (or DUMP env var)
  --mode preview|apply|validate default: preview; apply requires --yes or confirmation
  --tables all|<csv>            hard selection scope; staging/classification still use all preserved tables
  --include-classes <csv>       when supplied, limit selection to these classes
  --exclude-classes <csv>       remove classes after selection-file/include processing
  --selection-file <path>       generated/edited candidates, bounded by explicit table/class scope
  --only-corps <path>           restrict selected corp-bearing rows to listed corp identifiers
  --sample-size <n>             preview sample limit; default: 20
  --details-limit <n>           detail rows per table/class; default: 10000
  --selector-suggestion-limit <n>
                                exact manifest suggestions per table/class; default: 50
                                0 disables exact suggestions; maximum: 100000
  --no-aligned-details          do not create fixed-width .txt detail companions
  --align-width <n>             aligned detail cell width; default: 40, minimum: 6
  --manifest-default <new,changed|none>
                                generated selection default; default: new,changed
  --report-dir <dir>            base directory for run artifacts
  --keep-artifacts              retain delta schemas after successful apply
  --yes                         skip interactive apply confirmation
  --cleanup                     drop delta_stage/delta_map/delta_diff/delta_ctl and exit
  -h, --help                    show this help

Exit codes reserved by the plan:
  0 ok · 2 preflight/drift/corrupt dump · 3 advisory lock busy · 4 selection invalid · 5 apply verification failed

Environment:
  PGHOST, PGPORT, PGUSER, PGDATABASE, PGPASSWORD/.pgpass   libpq connection settings
  PG_BIN=/path/to/postgresql/bin     optional PostgreSQL client-tools directory; unset or empty uses PATH
  DUMP=<path>                        alternative to --dump
  LOCK_TIMEOUT_SECONDS=30            advisory-lock wait before exit 3

After run-directory initialization, each invocation prints its artifact directory on exit:
  Artifacts: <run-dir>            (success)
  Artifacts retained for inspection: <run-dir>   (failure)
USAGE
}

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

pg_conn_opts() {
  printf -- "-h %s -p %s -d %s -U %s" "$PGHOST" "$PGPORT" "$PGDATABASE" "$PGUSER"
}

is_identifier() {
  local val="$1"
  case "$val" in
    ''|*[!a-z0-9_]*|[0-9]*) return 1 ;;
    *) return 0 ;;
  esac
}

table_in_file() {
  local needle="$1" file="$2"
  grep -qx -- "$needle" "$file"
}

sql_literal() {
  local value="$1"
  printf "'%s'" "$(printf '%s' "$value" | sed "s/'/''/g")"
}

sha256_file() {
  local path="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$path" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$path" | awk '{print $1}'
  else
    die2 "neither sha256sum nor shasum is available to verify the dump"
  fi
}

psql_file() {
  local path="$1"
  "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 -f "$path"
}

psql_cmd() {
  local sql="$1"
  "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 -c "$sql"
}

psql_delta_session_file() {
  local payload="$1" stdout_path="$2" stderr_path="$3"
  shift 3

  if [[ "$stderr_path" = "-" ]]; then
    "$PSQL_BIN" -X -q $(pg_conn_opts) -v ON_ERROR_STOP=1 "$@" \
      -f "$SESSION_BEGIN_SQL" -f "$payload" -f "$SESSION_END_SQL" > "$stdout_path"
  else
    local status
    if "$PSQL_BIN" -X -q $(pg_conn_opts) -v ON_ERROR_STOP=1 "$@" \
         -f "$SESSION_BEGIN_SQL" -f "$payload" -f "$SESSION_END_SQL" \
         > "$stdout_path" 2> "$stderr_path"; then
      status=0
    else
      status=$?
    fi
    cat "$stderr_path" >&2
    return "$status"
  fi
}

record_temp_stats_snapshot() {
  local snapshot="$1"
  "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 -tA -F $'\t' >> "$RUN_DIR/temp_stats.tsv" <<SQL
SELECT now(), '$snapshot', datname, temp_files, temp_bytes, pg_size_pretty(temp_bytes)
FROM pg_stat_database
WHERE datname = current_database();
SQL
}

parse_args() {
  local arg
  while [[ "$#" -gt 0 ]]; do
    arg="$1"
    case "$arg" in
      --dump)
        [[ "$#" -ge 2 ]] || die "--dump requires a path"
        DUMP="$2"
        shift 2
        ;;
      --mode)
        [[ "$#" -ge 2 ]] || die "--mode requires preview, apply, or validate"
        MODE="$2"
        shift 2
        ;;
      --tables)
        [[ "$#" -ge 2 ]] || die "--tables requires all or a comma-separated list"
        TABLES_ARG="$2"
        shift 2
        ;;
      --include-classes)
        [[ "$#" -ge 2 ]] || die "--include-classes requires a comma-separated list"
        INCLUDE_CLASSES="$2"
        shift 2
        ;;
      --exclude-classes)
        [[ "$#" -ge 2 ]] || die "--exclude-classes requires a comma-separated list"
        EXCLUDE_CLASSES="$2"
        shift 2
        ;;
      --selection-file)
        [[ "$#" -ge 2 ]] || die "--selection-file requires a path"
        SELECTION_FILE="$2"
        shift 2
        ;;
      --only-corps)
        [[ "$#" -ge 2 ]] || die "--only-corps requires a path"
        ONLY_CORPS_FILE="$2"
        shift 2
        ;;
      --sample-size)
        [[ "$#" -ge 2 ]] || die "--sample-size requires a number"
        SAMPLE_SIZE="$2"
        shift 2
        ;;
      --details-limit)
        [[ "$#" -ge 2 ]] || die "--details-limit requires a number"
        DETAILS_LIMIT="$2"
        shift 2
        ;;
      --selector-suggestion-limit)
        [[ "$#" -ge 2 ]] || die "--selector-suggestion-limit requires a number"
        SELECTOR_SUGGESTION_LIMIT="$2"
        shift 2
        ;;
      --no-aligned-details)
        ALIGN_DETAILS="false"
        shift
        ;;
      --align-width)
        [[ "$#" -ge 2 ]] || die "--align-width requires a number"
        ALIGN_WIDTH="$2"
        shift 2
        ;;
      --manifest-default)
        [[ "$#" -ge 2 ]] || die "--manifest-default requires new,changed or none"
        MANIFEST_DEFAULT="$2"
        shift 2
        ;;
      --report-dir)
        [[ "$#" -ge 2 ]] || die "--report-dir requires a directory"
        REPORT_BASE="$2"
        shift 2
        ;;
      --keep-artifacts)
        KEEP_ARTIFACTS="true"
        shift
        ;;
      --yes)
        YES="true"
        shift
        ;;
      --cleanup)
        CLEANUP="true"
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "unknown argument: $arg"
        ;;
    esac
  done

  case "$MODE" in
    preview|apply|validate) ;;
    *) die "--mode must be preview, apply, or validate" ;;
  esac

  case "$MANIFEST_DEFAULT" in
    new,changed|none) ;;
    *) die "--manifest-default must be new,changed or none" ;;
  esac

  case "$SAMPLE_SIZE" in
    ''|*[!0-9]*) die "--sample-size must be a non-negative integer" ;;
    *) ;;
  esac
  case "$DETAILS_LIMIT" in
    ''|*[!0-9]*) die "--details-limit must be a non-negative integer" ;;
    *) ;;
  esac
  case "$SELECTOR_SUGGESTION_LIMIT" in
    ''|*[!0-9]*)
      die "--selector-suggestion-limit must be a decimal integer from 0 to $SELECTOR_SUGGESTION_LIMIT_MAX"
      ;;
    *)
      SELECTOR_SUGGESTION_LIMIT="${SELECTOR_SUGGESTION_LIMIT#"${SELECTOR_SUGGESTION_LIMIT%%[!0]*}"}"
      [[ -n "$SELECTOR_SUGGESTION_LIMIT" ]] || SELECTOR_SUGGESTION_LIMIT="0"
      if [[ "${#SELECTOR_SUGGESTION_LIMIT}" -gt "${#SELECTOR_SUGGESTION_LIMIT_MAX}" ]] \
         || (( 10#$SELECTOR_SUGGESTION_LIMIT > SELECTOR_SUGGESTION_LIMIT_MAX )); then
        die "--selector-suggestion-limit must be a decimal integer from 0 to $SELECTOR_SUGGESTION_LIMIT_MAX"
      fi
      ;;
  esac
  case "$ALIGN_WIDTH" in
    ''|*[!0-9]*) die "--align-width must be a positive integer" ;;
    *)
      while [[ "$ALIGN_WIDTH" = 0* && "$ALIGN_WIDTH" != "0" ]]; do
        ALIGN_WIDTH="${ALIGN_WIDTH#0}"
      done
      case "$ALIGN_WIDTH" in
        0) die "--align-width must be a positive integer" ;;
        [1-5]) ALIGN_WIDTH="6" ;;
      esac
      ;;
  esac
}

validate_static_files() {
  [[ -f "$PRESERVED_TABLES_CONF" ]] || die2 "missing preserved table config: $PRESERVED_TABLES_CONF"
  [[ -f "$INSTALL_SQL" ]] || die2 "missing install SQL: $INSTALL_SQL"
  [[ -f "$FUNCTIONS_SQL" ]] || die2 "missing classification functions SQL: $FUNCTIONS_SQL"
  [[ -f "$SESSION_BEGIN_SQL" ]] || die2 "missing session begin SQL: $SESSION_BEGIN_SQL"
  [[ -f "$SESSION_END_SQL" ]] || die2 "missing session end SQL: $SESSION_END_SQL"
  [[ -f "$REWRITE_AWK" ]] || die2 "missing COPY rewrite awk: $REWRITE_AWK"
  [[ -f "$ALIGN_DETAILS_AWK" ]] || die2 "missing detail alignment awk: $ALIGN_DETAILS_AWK"
  [[ -f "$REPAIR_SEQUENCES_SQL" ]] || die2 "missing repair sequences SQL: $REPAIR_SEQUENCES_SQL"
  [[ -f "$ACQUIRE_LOCK_SQL" ]] || die2 "missing advisory lock acquire SQL: $ACQUIRE_LOCK_SQL"
  [[ -f "$RELEASE_LOCK_SQL" ]] || die2 "missing advisory lock release SQL: $RELEASE_LOCK_SQL"
}

init_run_dir() {
  local ts
  ts="$(date -u +%Y%m%d_%H%M%S)"
  RUN_DIR="$REPORT_BASE/$ts"
  if [[ -e "$RUN_DIR" ]]; then
    RUN_DIR="$REPORT_BASE/${ts}_$$"
  fi
  mkdir -p "$RUN_DIR"
}

release_lock() {
  if [[ "$LOCK_ACQUIRED" = "true" ]]; then
    printf "\\i %s\n\\q\n" "$RELEASE_LOCK_SQL" >&3 2>/dev/null || true
    exec 3>&- 2>/dev/null || true
    wait "$LOCK_PID" >/dev/null 2>&1 || true
    LOCK_ACQUIRED="false"
  elif [[ -n "${LOCK_PID:-}" ]] && kill -0 "$LOCK_PID" >/dev/null 2>&1; then
    kill "$LOCK_PID" >/dev/null 2>&1 || true
    wait "$LOCK_PID" >/dev/null 2>&1 || true
  fi
}

on_exit() {
  local status=$?
  release_lock
  if [[ -n "$RUN_DIR" ]]; then
    if [[ "$status" -eq 0 ]]; then
      printf "Artifacts: %s\n" "$RUN_DIR"
    else
      printf >&2 "Artifacts retained for inspection: %s\n" "$RUN_DIR"
    fi
  fi
}

acquire_lock() {
  LOCK_FIFO="$RUN_DIR/advisory_lock.fifo"
  rm -f "$LOCK_FIFO"
  mkfifo "$LOCK_FIFO"

  "$PSQL_BIN" -X $(pg_conn_opts) -q -v ON_ERROR_STOP=1 \
    > "$RUN_DIR/advisory_lock.out" \
    2> "$RUN_DIR/advisory_lock.err" \
    < "$LOCK_FIFO" &
  LOCK_PID=$!

  exec 3>"$LOCK_FIFO"
  rm -f "$RUN_DIR/advisory_lock.acquired"
  printf "\\i %s\n\\! touch %s\n" "$ACQUIRE_LOCK_SQL" "$RUN_DIR/advisory_lock.acquired" >&3

  local waited=0
  while [[ "$waited" -lt "$LOCK_TIMEOUT_SECONDS" ]]; do
    if [[ -f "$RUN_DIR/advisory_lock.acquired" ]]; then
      LOCK_ACQUIRED="true"
      printf "🔒  Advisory lock acquired.\n"
      return 0
    fi
    if ! kill -0 "$LOCK_PID" >/dev/null 2>&1; then
      cat "$RUN_DIR/advisory_lock.err" >&2 2>/dev/null || true
      die3 "failed to acquire advisory lock"
    fi
    sleep 1
    waited=$((waited + 1))
  done

  cat "$RUN_DIR/advisory_lock.err" >&2 2>/dev/null || true
  die3 "timed out waiting for the subset/full-refresh advisory lock after ${LOCK_TIMEOUT_SECONDS}s"
}

load_preserved_config() {
  local table phase _rest
  : > "$RUN_DIR/preserved_tables.tsv"
  : > "$RUN_DIR/all_conf_tables.txt"

  while read -r table phase _rest; do
    case "${table:-}" in
      ''|'#'*) continue ;;
      *) ;;
    esac
    is_identifier "$table" || die2 "invalid table name in $PRESERVED_TABLES_CONF: $table"
    case "${phase:-}" in
      ''|*[!0-9]*) die2 "invalid load phase for $table in $PRESERVED_TABLES_CONF: ${phase:-<missing>}" ;;
      *) ;;
    esac
    printf "%s\t%s\n" "$table" "$phase" >> "$RUN_DIR/preserved_tables.tsv"
    printf "%s\n" "$table" >> "$RUN_DIR/all_conf_tables.txt"
  done < "$PRESERVED_TABLES_CONF"

  [[ -s "$RUN_DIR/preserved_tables.tsv" ]] || die2 "no preserved tables found in $PRESERVED_TABLES_CONF"
}

select_tables() {
  # Preview classification stages the full preserved set so parent ID maps exist
  # even when a future selection narrows to --tables. Keep the requested list as
  # an artifact for later selection/reporting work, but do not starve staging.
  cp "$RUN_DIR/all_conf_tables.txt" "$RUN_DIR/selected_tables.txt"
  : > "$RUN_DIR/requested_tables.txt"

  if [[ "$TABLES_ARG" = "all" ]]; then
    cp "$RUN_DIR/all_conf_tables.txt" "$RUN_DIR/requested_tables.txt"
    return 0
  fi

  local old_ifs item
  old_ifs="$IFS"
  IFS=','
  # shellcheck disable=SC2206
  set -- $TABLES_ARG
  IFS="$old_ifs"

  [[ "$#" -gt 0 ]] || die2 "--tables did not include any table names"
  for item in "$@"; do
    item="$(printf '%s' "$item" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
    is_identifier "$item" || die2 "invalid --tables entry: $item"
    table_in_file "$item" "$RUN_DIR/all_conf_tables.txt" || die2 "--tables entry is not in preserved_tables.conf: $item"
    if ! table_in_file "$item" "$RUN_DIR/requested_tables.txt"; then
      printf "%s\n" "$item" >> "$RUN_DIR/requested_tables.txt"
    fi
  done
}

seed_table_config() {
  "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 \
    -c "COPY delta_ctl.table_config(table_name, load_phase) FROM STDIN" \
    < "$RUN_DIR/preserved_tables.tsv"

  cat > "$RUN_DIR/seed_table_config_metadata.sql" <<'SQL'
UPDATE delta_ctl.table_config SET pk_col = 'id' WHERE table_name IN (
  'demigrated_filings', 'bad_emails', 'excluded_email_domain_patterns', 'mig_group', 'mig_batch',
  'mig_corp_batch', 'mig_corp_account', 'corp_processing', 'colin_tracking',
  'auth_processing', 'auth_component_operation'
);
UPDATE delta_ctl.table_config SET has_last_modified = true WHERE table_name IN (
  'corp_processing', 'colin_tracking', 'auth_processing'
);
UPDATE delta_ctl.table_config SET match_mode = 'hash_parent' WHERE table_name = 'auth_component_operation';
UPDATE delta_ctl.table_config SET nk_enforced = true WHERE table_name IN (
  'demigrated_filings', 'bad_emails', 'excluded_emails', 'excluded_email_domains',
  'excluded_email_domain_patterns', 'corp_processing', 'colin_tracking',
  'auth_processing'
);
UPDATE delta_ctl.table_config SET fk_map = '{"mig_group_id":"mig_group"}'::jsonb WHERE table_name = 'mig_batch';
UPDATE delta_ctl.table_config SET fk_map = '{"mig_batch_id":"mig_batch"}'::jsonb WHERE table_name IN (
  'mig_corp_batch', 'mig_corp_account'
);
UPDATE delta_ctl.table_config SET fk_map = '{"mig_batch_id":"mig_batch","corp_num":"external:corporation.corp_num","last_processed_event_id":"external:event.event_id","failed_event_id":"external:event.event_id"}'::jsonb WHERE table_name = 'corp_processing';
UPDATE delta_ctl.table_config SET fk_map = '{"mig_batch_id":"mig_batch","corp_num":"external:corporation.corp_num"}'::jsonb WHERE table_name IN (
  'colin_tracking', 'auth_processing'
);
UPDATE delta_ctl.table_config SET fk_map = '{"auth_processing_id":"auth_processing"}'::jsonb WHERE table_name = 'auth_component_operation';
SQL
  psql_file "$RUN_DIR/seed_table_config_metadata.sql"
}

record_metadata() {
  cat > "$RUN_DIR/metadata.sql" <<SQL
INSERT INTO delta_ctl.run_metadata(key, value) VALUES
  ('mode', $(sql_literal "$MODE")),
  ('dump_path', $(sql_literal "$DUMP")),
  ('dump_sha256', $(sql_literal "$DUMP_SHA256")),
  ('manifest_default', $(sql_literal "$MANIFEST_DEFAULT")),
  ('selector_suggestion_limit', $(sql_literal "$SELECTOR_SUGGESTION_LIMIT")),
  ('selection_file', $(sql_literal "$SELECTION_FILE")),
  ('run_dir', $(sql_literal "$RUN_DIR")),
  ('target_host', $(sql_literal "$PGHOST")),
  ('target_port', $(sql_literal "$PGPORT")),
  ('target_database', $(sql_literal "$PGDATABASE")),
  ('target_user', $(sql_literal "$PGUSER"))
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, created_at = now();
SQL
  psql_file "$RUN_DIR/metadata.sql"
}

cleanup_schemas() {
  printf "🧹  Dropping delta schemas …\n"
  "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 <<'SQL'
DROP SCHEMA IF EXISTS delta_stage CASCADE;
DROP SCHEMA IF EXISTS delta_map CASCADE;
DROP SCHEMA IF EXISTS delta_diff CASCADE;
DROP SCHEMA IF EXISTS delta_ctl CASCADE;
SQL
  printf "✅  Cleanup complete.\n"
}

compute_dump_sha() {
  [[ -n "$DUMP" ]] || die2 "--dump is required for preview/apply/validate mode"
  [[ -r "$DUMP" ]] || die2 "dump is not readable: $DUMP"

  local computed_sha
  computed_sha="$(sha256_file "$DUMP")" || return $?
  [[ -n "$computed_sha" ]] || die2 "could not compute dump sha256: $DUMP"
  DUMP_SHA256="$computed_sha"
  printf '%s\n' "$DUMP_SHA256" > "$RUN_DIR/dump.sha256"
}

verify_dump_and_manifest() {
  [[ -n "$DUMP" ]] || die2 "--dump is required for preview/apply/validate mode"
  [[ -r "$DUMP" ]] || die2 "dump is not readable: $DUMP"

  printf "🔎  Reading dump TOC …\n"
  "$PG_RESTORE_BIN" -l "$DUMP" > "$RUN_DIR/toc.list" || die2 "pg_restore could not read dump: $DUMP"

  local manifest expected_sha actual_sha
  compute_dump_sha
  manifest="$DUMP.manifest.json"
  if [[ -f "$manifest" ]]; then
    cp "$manifest" "$RUN_DIR/dump.manifest.json"
    expected_sha="$(sed -n 's/.*"dump_sha256"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$manifest" | head -n 1)"
    if [[ -n "$expected_sha" ]]; then
      actual_sha="$DUMP_SHA256"
      if [[ "$expected_sha" != "$actual_sha" ]]; then
        die2 "dump sha256 does not match manifest: expected $expected_sha, got $actual_sha"
      fi
      printf "🧾  Manifest sha256 verified.\n"
    else
      printf "⚠️  Manifest found but dump_sha256 was not present: %s\n" "$manifest" | tee -a "$RUN_DIR/warnings.log"
    fi
  fi
}

filter_toc() {
  : > "$RUN_DIR/toc_data.list"
  : > "$RUN_DIR/present_tables.txt"
  : > "$RUN_DIR/absent_tables.txt"
  : > "$RUN_DIR/unexpected_dump_tables.txt"

  awk -v selected="$RUN_DIR/selected_tables.txt" \
      -v all_conf="$RUN_DIR/all_conf_tables.txt" \
      -v present="$RUN_DIR/present_tables.txt" \
      -v unexpected="$RUN_DIR/unexpected_dump_tables.txt" '
    BEGIN {
      while ((getline t < selected) > 0) selected_table[t] = 1
      close(selected)
      while ((getline t < all_conf) > 0) conf_table[t] = 1
      close(all_conf)
    }
    $0 ~ / TABLE DATA public / {
      t = $0
      sub(/^.* TABLE DATA public /, "", t)
      sub(/ .*/, "", t)
      if (selected_table[t]) {
        print $0
        if (!seen[t]++) print t >> present
      } else if (!conf_table[t]) {
        if (!warned[t]++) print t >> unexpected
      }
    }
  ' "$RUN_DIR/toc.list" > "$RUN_DIR/toc_data.list"

  while read -r table; do
    [[ -n "$table" ]] || continue
    if ! table_in_file "$table" "$RUN_DIR/present_tables.txt"; then
      printf "%s\n" "$table" >> "$RUN_DIR/absent_tables.txt"
    fi
  done < "$RUN_DIR/selected_tables.txt"

  if [[ -s "$RUN_DIR/unexpected_dump_tables.txt" ]]; then
    printf "⚠️  Dump contains table data outside preserved_tables.conf; excluding:\n" | tee -a "$RUN_DIR/warnings.log"
    sed 's/^/  - /' "$RUN_DIR/unexpected_dump_tables.txt" | tee -a "$RUN_DIR/warnings.log"
  fi
  if [[ -s "$RUN_DIR/absent_tables.txt" ]]; then
    printf "ℹ️  Preserved table(s) absent from dump; marking SKIPPED_ABSENT:\n" | tee -a "$RUN_DIR/warnings.log"
    sed 's/^/  - /' "$RUN_DIR/absent_tables.txt" | tee -a "$RUN_DIR/warnings.log"
  fi
}

install_control_schemas() {
  printf "🏗  Installing delta control schemas …\n"
  psql_file "$INSTALL_SQL"
  psql_file "$FUNCTIONS_SQL"
  seed_table_config
  record_metadata
}

create_stage_shells() {
  : > "$RUN_DIR/create_stage_shells.sql"

  if [[ ! -s "$RUN_DIR/present_tables.txt" ]]; then
    printf "ℹ️  No selected preserved table data was present in the dump; skipping stage shell creation.\n"
    return 0
  fi

  cat > "$RUN_DIR/create_stage_shells.sql" <<'SQL'
DO $$
DECLARE
  missing text[];
BEGIN
  SELECT array_agg(v.table_name ORDER BY v.table_name)
    INTO missing
  FROM (VALUES
SQL

  local first="true" table
  while read -r table; do
    [[ -n "$table" ]] || continue
    if [[ "$first" = "true" ]]; then
      first="false"
    else
      printf ",\n" >> "$RUN_DIR/create_stage_shells.sql"
    fi
    printf "    (%s)" "$(sql_literal "$table")" >> "$RUN_DIR/create_stage_shells.sql"
  done < "$RUN_DIR/present_tables.txt"

  cat >> "$RUN_DIR/create_stage_shells.sql" <<'SQL'
  ) AS v(table_name)
  WHERE to_regclass(format('public.%I', v.table_name)) IS NULL;

  IF missing IS NOT NULL THEN
    RAISE EXCEPTION 'local preserved table(s) missing: %. Apply the latest colin_corps_extract_postgres_ddl first.', array_to_string(missing, ', ');
  END IF;
END;
$$;
SQL

  while read -r table; do
    [[ -n "$table" ]] || continue
    cat >> "$RUN_DIR/create_stage_shells.sql" <<SQL
CREATE UNLOGGED TABLE delta_stage.$table (LIKE public.$table INCLUDING DEFAULTS);
ALTER TABLE delta_stage.$table ADD COLUMN _delta_row_id bigint GENERATED ALWAYS AS IDENTITY;
SQL
  done < "$RUN_DIR/present_tables.txt"

  psql_file "$RUN_DIR/create_stage_shells.sql" || die2 "failed to create delta_stage shells; apply the latest colin_corps_extract_postgres_ddl first"
}

load_dump_columns_sidecar() {
  : > "$RUN_DIR/dump_columns_rows.tsv"
  if [[ -f "$RUN_DIR/dump_columns.tsv" ]]; then
    awk -F '\t' '
      NF >= 2 {
        n = split($2, cols, ",")
        for (i = 1; i <= n; i++) {
          gsub(/^[[:space:]]+|[[:space:]]+$/, "", cols[i])
          if (cols[i] != "") print $1 "\t" cols[i] "\t" i
        }
      }
    ' "$RUN_DIR/dump_columns.tsv" > "$RUN_DIR/dump_columns_rows.tsv"
  fi

  psql_cmd "TRUNCATE delta_ctl.dump_columns"
  if [[ -s "$RUN_DIR/dump_columns_rows.tsv" ]]; then
    "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 \
      -c "COPY delta_ctl.dump_columns(table_name, column_name, ordinal) FROM STDIN" \
      < "$RUN_DIR/dump_columns_rows.tsv"
  fi
}

run_schema_drift_preflight() {
  load_dump_columns_sidecar

  "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 -tA -F $'\t' > "$RUN_DIR/drift_dump_only.tsv" <<'SQL'
SELECT d.table_name, d.column_name
FROM delta_ctl.dump_columns d
LEFT JOIN information_schema.columns c
  ON c.table_schema = 'public'
 AND c.table_name = d.table_name
 AND c.column_name = d.column_name
WHERE c.column_name IS NULL
ORDER BY d.table_name, d.ordinal;
SQL

  "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 -tA -F $'\t' > "$RUN_DIR/drift_local_required.tsv" <<'SQL'
SELECT c.table_name, c.column_name
FROM information_schema.columns c
JOIN (SELECT DISTINCT table_name FROM delta_ctl.dump_columns) d0 ON d0.table_name = c.table_name
LEFT JOIN delta_ctl.dump_columns d
  ON d.table_name = c.table_name
 AND d.column_name = c.column_name
WHERE c.table_schema = 'public'
  AND d.column_name IS NULL
  AND c.is_nullable = 'NO'
  AND c.column_default IS NULL
  AND c.identity_generation IS NULL
ORDER BY c.table_name, c.ordinal_position;
SQL

  "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 -tA -F $'\t' > "$RUN_DIR/drift_local_copy_permitted.tsv" <<'SQL'
SELECT c.table_name, c.column_name,
       CASE
         WHEN c.column_default IS NOT NULL THEN 'local-only column has a default; staged rows used local default'
         WHEN c.identity_generation IS NOT NULL THEN 'local-only identity column; staged rows used local identity/default behavior'
         ELSE 'local-only nullable column; staged rows used NULL'
       END AS warning
FROM information_schema.columns c
JOIN (SELECT DISTINCT table_name FROM delta_ctl.dump_columns) d0 ON d0.table_name = c.table_name
LEFT JOIN delta_ctl.dump_columns d
  ON d.table_name = c.table_name
 AND d.column_name = c.column_name
WHERE c.table_schema = 'public'
  AND d.column_name IS NULL
  AND NOT (c.is_nullable = 'NO' AND c.column_default IS NULL AND c.identity_generation IS NULL)
ORDER BY c.table_name, c.ordinal_position;
SQL

  if [[ -s "$RUN_DIR/drift_dump_only.tsv" ]]; then
    printf >&2 "Dump contains column(s) not present in local DDL. Apply latest colin_corps_extract_postgres_ddl first:\n"
    sed 's/^/  /' "$RUN_DIR/drift_dump_only.tsv" >&2
    return 2
  fi

  if [[ -s "$RUN_DIR/drift_local_required.tsv" ]]; then
    printf >&2 "Local DDL has required column(s) missing from the dump. Regenerate the preserved-table dump:\n"
    sed 's/^/  /' "$RUN_DIR/drift_local_required.tsv" >&2
    return 2
  fi

  if [[ -s "$RUN_DIR/drift_local_copy_permitted.tsv" ]]; then
    printf "⚠️  Local-only copy-permitted column(s) detected; adding to classify_ignore_cols for this run:\n" | tee -a "$RUN_DIR/warnings.log"
    sed 's/^/  /' "$RUN_DIR/drift_local_copy_permitted.tsv" | tee -a "$RUN_DIR/warnings.log"

    "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 <<'SQL'
WITH local_only AS (
  SELECT c.table_name, c.column_name,
         CASE
           WHEN c.column_default IS NOT NULL THEN 'local-only column has a default; staged rows used local default'
           WHEN c.identity_generation IS NOT NULL THEN 'local-only identity column; staged rows used local identity/default behavior'
           ELSE 'local-only nullable column; staged rows used NULL'
         END AS warning
  FROM information_schema.columns c
  JOIN (SELECT DISTINCT table_name FROM delta_ctl.dump_columns) d0 ON d0.table_name = c.table_name
  LEFT JOIN delta_ctl.dump_columns d
    ON d.table_name = c.table_name
   AND d.column_name = c.column_name
  WHERE c.table_schema = 'public'
    AND d.column_name IS NULL
    AND NOT (c.is_nullable = 'NO' AND c.column_default IS NULL AND c.identity_generation IS NULL)
), grouped AS (
  SELECT table_name, array_agg(column_name ORDER BY column_name) AS cols
  FROM local_only
  GROUP BY table_name
)
INSERT INTO delta_ctl.drift_warnings(table_name, column_name, warning)
SELECT table_name, column_name, warning FROM local_only;

UPDATE delta_ctl.table_config t
SET classify_ignore_cols = (
  SELECT ARRAY(
    SELECT DISTINCT unnest(t.classify_ignore_cols || g.cols)
    ORDER BY 1
  )
)
FROM grouped g
WHERE g.table_name = t.table_name;
SQL
  fi

  return 0
}

add_stage_index() {
  local table="$1" index_name="$2" columns="$3"
  if table_in_file "$table" "$RUN_DIR/present_tables.txt"; then
    printf 'CREATE INDEX IF NOT EXISTS %s ON delta_stage.%s (%s);\n' "$index_name" "$table" "$columns" >> "$RUN_DIR/create_stage_indexes.sql"
  fi
}

create_stage_indexes() {
  : > "$RUN_DIR/create_stage_indexes.sql"

  local table
  while read -r table; do
    [[ -n "$table" ]] || continue
    add_stage_index "$table" "idx_delta_stage_${table}_drid" "_delta_row_id"
  done < "$RUN_DIR/present_tables.txt"

  add_stage_index demigrated_filings idx_delta_stage_demigrated_filings_nk "filing_id"
  add_stage_index email_domain_groups idx_delta_stage_email_domain_groups_nk "email_domain"
  add_stage_index bad_emails idx_delta_stage_bad_emails_nk "lower(btrim(email))"
  add_stage_index excluded_emails idx_delta_stage_excluded_emails_nk "lower(btrim(email))"
  add_stage_index excluded_email_domains idx_delta_stage_excluded_email_domains_nk "lower(btrim(email_domain))"
  add_stage_index excluded_email_domain_patterns idx_delta_stage_excluded_email_domain_patterns_nk "lower(btrim(email_domain)), lower(btrim(local_part_pattern))"
  add_stage_index exclude_corps idx_delta_stage_exclude_corps_nk "corp_num"
  add_stage_index corps_with_third_party idx_delta_stage_corps_with_third_party_nk "corp_num, vendor"
  add_stage_index bar_corps idx_delta_stage_bar_corps_nk "identifier"
  add_stage_index mig_group idx_delta_stage_mig_group_nk "name, target_environment, source_db"
  add_stage_index mig_batch idx_delta_stage_mig_batch_nk "mig_group_id, name, target_environment"
  add_stage_index mig_corp_batch idx_delta_stage_mig_corp_batch_nk "mig_batch_id, corp_num"
  add_stage_index mig_corp_account idx_delta_stage_mig_corp_account_nk "corp_num, target_environment, account_id, mig_batch_id"
  add_stage_index corp_processing idx_delta_stage_corp_processing_nk "corp_num, flow_name, environment"
  add_stage_index colin_tracking idx_delta_stage_colin_tracking_nk "corp_num, flow_name, environment"
  add_stage_index auth_processing idx_delta_stage_auth_processing_nk "corp_num, flow_name, environment, operation, operation_scope, attempt_key"
  add_stage_index auth_component_operation idx_delta_stage_auth_component_operation_parent "auth_processing_id"

  if [[ -s "$RUN_DIR/create_stage_indexes.sql" ]]; then
    printf "⚙️  Creating delta_stage classification indexes …\n"
    psql_file "$RUN_DIR/create_stage_indexes.sql"
  fi
}

stream_stage_data() {
  if [[ ! -s "$RUN_DIR/toc_data.list" ]]; then
    printf "ℹ️  No TABLE DATA entries selected for staging.\n"
    return 0
  fi

  cp "$RUN_DIR/present_tables.txt" "$RUN_DIR/expected_tables.txt"
  printf "🚚  Streaming dump data into delta_stage …\n"

  if ! {
      set +e
      "$PG_RESTORE_BIN" --data-only -L "$RUN_DIR/toc_data.list" -f - "$DUMP" \
        | awk -f "$REWRITE_AWK" -v sidecar="$RUN_DIR/dump_columns.tsv" -v expected="$RUN_DIR/expected_tables.txt"
      pipeline_status=("${PIPESTATUS[@]}")
      pg_restore_status=${pipeline_status[0]}
      awk_status=${pipeline_status[1]}
      set -e

      if [[ "$pg_restore_status" -eq 0 && "$awk_status" -eq 0 ]]; then
        printf "SELECT 1 AS delta_stream_complete;\n"
        exit 0
      fi

      printf >&2 "staging producer failed: pg_restore=%s awk=%s\n" "$pg_restore_status" "$awk_status"
      printf "SELECT 1/0 AS delta_stream_failed;\n"
      exit 2
    } | "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 --single-transaction -q \
          -f "$SESSION_BEGIN_SQL" -f - -f "$SESSION_END_SQL"; then
    printf >&2 "Staging stream failed; running sidecar drift diagnostics where possible.\n"
    run_schema_drift_preflight || true
    die2 "failed to stream dump data into delta_stage"
  fi

  run_schema_drift_preflight || die2 "schema drift preflight failed"
}

record_stage_counts() {
  : > "$RUN_DIR/stage_counts.sql"

  while read -r table; do
    [[ -n "$table" ]] || continue
    cat >> "$RUN_DIR/stage_counts.sql" <<SQL
INSERT INTO delta_ctl.run_counts(table_name, count_name, row_count)
SELECT '$table', 'STAGED', count(*) FROM delta_stage.$table
ON CONFLICT (table_name, count_name) DO UPDATE SET row_count = EXCLUDED.row_count, created_at = now();
ANALYZE delta_stage.$table;
SQL
  done < "$RUN_DIR/present_tables.txt"

  while read -r table; do
    [[ -n "$table" ]] || continue
    cat >> "$RUN_DIR/stage_counts.sql" <<SQL
INSERT INTO delta_ctl.run_counts(table_name, count_name, row_count, details)
VALUES ('$table', 'SKIPPED_ABSENT', 0, '{"reason":"table data absent from dump"}'::jsonb)
ON CONFLICT (table_name, count_name) DO UPDATE SET row_count = EXCLUDED.row_count, details = EXCLUDED.details, created_at = now();
SQL
  done < "$RUN_DIR/absent_tables.txt"

  if [[ -s "$RUN_DIR/stage_counts.sql" ]]; then
    psql_file "$RUN_DIR/stage_counts.sql"
  fi

  "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 -tA -F $'\t' > "$RUN_DIR/stage_counts.tsv" <<'SQL'
SELECT table_name, count_name, row_count
FROM delta_ctl.run_counts
WHERE count_name IN ('STAGED', 'SKIPPED_ABSENT')
ORDER BY table_name, count_name;
SQL
}

run_preview_classification() {
  printf "🧮  Classifying staged rows …\n"
  cat > "$RUN_DIR/preview_classification.sql" <<'SQL'
SELECT delta_ctl.run_preview_classification();
SQL
  printf "captured_at\tsnapshot\tdatname\ttemp_files\ttemp_bytes\ttemp_bytes_pretty\n" > "$RUN_DIR/temp_stats.tsv"
  record_temp_stats_snapshot "before_classification"

  set +e
  psql_delta_session_file "$RUN_DIR/preview_classification.sql" \
    "$RUN_DIR/classification.out" "$RUN_DIR/classification.err"
  local classification_status=$?
  set -e

  record_temp_stats_snapshot "after_classification" || true
  [[ "$classification_status" -eq 0 ]] || return "$classification_status"

  "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 -tA -F $'\t' > "$RUN_DIR/class_counts.tsv" <<'SQL'
SELECT table_name, count_name, row_count, load_phase
FROM delta_ctl.fn_counts();
SQL
}

write_selection_manifest() {
  printf "📝  Writing default selection manifest …\n"
  cat > "$RUN_DIR/render_selection_manifest.sql" <<'SQL'
SELECT * FROM delta_ctl.render_selection_manifest();
SQL
  psql_delta_session_file "$RUN_DIR/render_selection_manifest.sql" \
    "$RUN_DIR/selection.conf" "$RUN_DIR/selection_manifest.err" -tA
}

write_selection_cookbook() {
  printf "📖  Writing selection cookbook …\n"
  cat > "$RUN_DIR/render_selection_cookbook.sql" <<'SQL'
SELECT * FROM delta_ctl.render_selection_cookbook();
SQL
  psql_delta_session_file "$RUN_DIR/render_selection_cookbook.sql" \
    "$RUN_DIR/selection_cookbook.txt" "$RUN_DIR/selection_cookbook.err" -tA
}

write_aligned_detail() {
  local tsv_file="$1" total="$2" row_class="$3"
  local txt_file="${tsv_file%.tsv}.txt"
  local tmp_file="$txt_file.tmp"
  local err_file="$txt_file.err"
  local rendered truncated=""

  [[ "$ALIGN_DETAILS" = "true" && -s "$tsv_file" ]] || return 0

  if ! rendered="$(awk 'NR > 1 && $0 !~ /^#/ { count++ } END { print count + 0 }' "$tsv_file")"; then
    printf "⚠️  Could not count detail rows for aligned companion: %s\n" "$tsv_file" \
      | tee -a "$RUN_DIR/warnings.log" >&2 || true
    return 0
  fi
  if grep -q '^# TRUNCATED at ' "$tsv_file" || [[ "$total" -gt "$DETAILS_LIMIT" ]]; then
    truncated=" — TRUNCATED"
  fi

  if awk -v max_width="$ALIGN_WIDTH" -f "$ALIGN_DETAILS_AWK" "$tsv_file" "$tsv_file" \
       > "$tmp_file" 2> "$err_file" \
     && printf '# rendered %s of %s %s rows%s\n' \
          "$rendered" "$total" "$row_class" "$truncated" >> "$tmp_file" \
     && mv "$tmp_file" "$txt_file"; then
    rm -f "$err_file"
  else
    [[ ! -s "$err_file" ]] || cat "$err_file" >&2
    printf "⚠️  Could not create aligned detail companion for %s; canonical TSV retained.\n" "$tsv_file" \
      | tee -a "$RUN_DIR/warnings.log" >&2 || true
    rm -f "$tmp_file" "$err_file" "$txt_file"
  fi
  return 0
}

write_row_details() {
  local table new_n changed_n blocked_n sql_file out_file rel
  mkdir -p "$RUN_DIR/details"
  : > "$RUN_DIR/detail_artifacts.txt"
  while read -r table; do
    [[ -n "$table" ]] || continue
    new_n="$(awk -F '\t' -v t="$table" '$1 == t && $2 == "NEW" { print $3; exit }' "$RUN_DIR/class_counts.tsv")"
    changed_n="$(awk -F '\t' -v t="$table" '$1 == t && ($2 == "CHANGED" || $2 == "CHANGED_LOCAL_NEWER") { n += $3 } END { print n + 0 }' "$RUN_DIR/class_counts.tsv")"
    blocked_n="$(awk -F '\t' -v t="$table" '$1 == t && ($2 == "BLOCKED_FK" || $2 == "AMBIGUOUS_NK") { n += $3 } END { print n + 0 }' "$RUN_DIR/class_counts.tsv")"

    if [[ "${new_n:-0}" -gt 0 ]]; then
      rel="details/$table.new.tsv"; out_file="$RUN_DIR/$rel"; sql_file="$RUN_DIR/render_$table.new.sql"
      printf "SELECT * FROM delta_ctl.render_new_rows_tsv(%s, %s);\n" "$(sql_literal "$table")" "$DETAILS_LIMIT" > "$sql_file"
      psql_delta_session_file "$sql_file" "$out_file" "$RUN_DIR/render_$table.new.err" -tA
      write_aligned_detail "$out_file" "$new_n" "NEW"
      printf '%s\n' "$rel" >> "$RUN_DIR/detail_artifacts.txt"
    fi
    if [[ "$changed_n" -gt 0 ]]; then
      rel="details/$table.changed.tsv"; out_file="$RUN_DIR/$rel"; sql_file="$RUN_DIR/render_$table.changed.sql"
      printf "SELECT * FROM delta_ctl.render_changed_rows_tsv(%s, %s);\n" "$(sql_literal "$table")" "$DETAILS_LIMIT" > "$sql_file"
      psql_delta_session_file "$sql_file" "$out_file" "$RUN_DIR/render_$table.changed.err" -tA
      write_aligned_detail "$out_file" "$changed_n" "CHANGED"
      printf '%s\n' "$rel" >> "$RUN_DIR/detail_artifacts.txt"
    fi
    if [[ "$blocked_n" -gt 0 ]]; then
      rel="details/$table.blocked.tsv"; out_file="$RUN_DIR/$rel"; sql_file="$RUN_DIR/render_$table.blocked.sql"
      printf "SELECT * FROM delta_ctl.render_blocked_rows_tsv(%s, %s);\n" "$(sql_literal "$table")" "$DETAILS_LIMIT" > "$sql_file"
      psql_delta_session_file "$sql_file" "$out_file" "$RUN_DIR/render_$table.blocked.err" -tA
      write_aligned_detail "$out_file" "$blocked_n" "BLOCKED"
      printf '%s\n' "$rel" >> "$RUN_DIR/detail_artifacts.txt"
    fi
  done < "$RUN_DIR/present_tables.txt"
}

normalize_class_list() {
  local value="$1" out="$2"
  : > "$out"
  [[ -n "$value" ]] || return 0
  printf '%s\n' "$value" | awk -F',' '
    function trim(s) { gsub(/^[[:space:]]+|[[:space:]]+$/, "", s); return s }
    function cls(s) {
      s = tolower(trim(s))
      if (s == "new") return "NEW"
      if (s == "changed") return "CHANGED"
      if (s == "changed_local_newer" || s == "local_newer") return "CHANGED_LOCAL_NEWER"
      if (s == "") return ""
      printf("invalid apply class: %s\n", s) > "/dev/stderr"; exit 4
    }
    { for (i = 1; i <= NF; i++) { c = cls($i); if (c != "" && !seen[c]++) print c } }
  ' > "$out" || return 4
}

scope_selection_file_input() {
  [[ "$TABLES_ARG" != "all" || -n "$INCLUDE_CLASSES" || -n "$EXCLUDE_CLASSES" ]] || return 0

  local requested="$RUN_DIR/requested_tables.txt"
  local include_classes="$RUN_DIR/scope_include_classes.txt"
  local exclude_classes="$RUN_DIR/scope_exclude_classes.txt"
  local scoped="$RUN_DIR/selection_input.scoped.tsv"
  local restrict_include="false"

  [[ -r "$requested" ]] || die4 "requested table scope is unavailable; re-run preview"
  if [[ -n "$INCLUDE_CLASSES" ]]; then
    restrict_include="true"
  fi
  normalize_class_list "$INCLUDE_CLASSES" "$include_classes" || die4 "invalid --include-classes"
  normalize_class_list "$EXCLUDE_CLASSES" "$exclude_classes" || die4 "invalid --exclude-classes"

  awk -F '\t' \
      -v requested="$requested" \
      -v included="$include_classes" \
      -v excluded="$exclude_classes" \
      -v restrict_include="$restrict_include" '
    BEGIN {
      while ((getline value < requested) > 0) allowed_table[value] = 1
      close(requested)
      while ((getline value < included) > 0) allowed_class[value] = 1
      close(included)
      while ((getline value < excluded) > 0) denied_class[value] = 1
      close(excluded)
    }
    ($1 in allowed_table) &&
      (restrict_include != "true" || ($2 in allowed_class)) &&
      !($2 in denied_class) { print $0 }
  ' "$RUN_DIR/selection_input.tsv" > "$scoped" || die4 "could not enforce selection table/class scope"
  mv "$scoped" "$RUN_DIR/selection_input.tsv"
}

build_selection_input() {
  local base_classes="$RUN_DIR/base_classes.txt"
  local exclude_classes="$RUN_DIR/exclude_classes.txt"
  local requested="$RUN_DIR/requested_tables.txt"
  : > "$RUN_DIR/selection_input.tsv"
  : > "$RUN_DIR/row_selection_input.tsv"
  : > "$RUN_DIR/selection_header.tsv"

  if [[ -n "$SELECTION_FILE" ]]; then
    [[ -r "$SELECTION_FILE" ]] || die4 "selection file is not readable: $SELECTION_FILE"
    awk -v all_tables="$RUN_DIR/all_conf_tables.txt" \
        -v rowout="$RUN_DIR/row_selection_input.tsv" \
        -v headerout="$RUN_DIR/selection_header.tsv" '
      function trim(s) { gsub(/^[[:space:]]+|[[:space:]]+$/, "", s); return s }
      function cls(s) {
        s = tolower(trim(s))
        if (s == "new") return "NEW"
        if (s == "changed") return "CHANGED"
        if (s == "changed_local_newer" || s == "local_newer") return "CHANGED_LOCAL_NEWER"
        if (s == "") return ""
        fail("invalid apply class: " s)
      }
      function fail(message) {
        printf("selection line %s: %s\n", NR, message) > "/dev/stderr"
        failed = 1
        exit 4
      }
      function decimal_le(a, b, aa, bb, k, ad, bd) {
        aa = a; bb = b
        sub(/^0+/, "", aa); sub(/^0+/, "", bb)
        if (aa == "") aa = "0"; if (bb == "") bb = "0"
        if (length(aa) != length(bb)) return length(aa) < length(bb)
        for (k = 1; k <= length(aa); k++) {
          ad = substr(aa, k, 1) + 0; bd = substr(bb, k, 1) + 0
          if (ad != bd) return ad < bd
        }
        return 1
      }
      function copy_escape(s) {
        gsub(/\\/, "\\\\", s)
        gsub(/\t/, "\\t", s)
        gsub(/\r/, "\\r", s)
        return s
      }
      BEGIN {
        while ((getline t < all_tables) > 0) { valid[t] = 1; order[++n] = t }
        close(all_tables)
        wildcard = "NEW,CHANGED"
      }
      {
        raw = $0
        sub(/\r$/, "", raw)
        if (raw ~ /^[[:space:]]*#[[:space:]]*dump_sha256=/) {
          if (dump_header_seen++) fail("duplicate dump_sha256 header")
          value = raw
          sub(/^[[:space:]]*#[[:space:]]*dump_sha256=/, "", value)
          print "dump_sha256\t" trim(value) >> headerout
        } else if (raw ~ /^[[:space:]]*#[[:space:]]*staged[[:space:]]+/) {
          value = raw
          sub(/^[[:space:]]*#[[:space:]]*staged[[:space:]]+/, "", value)
          count = split(value, entries, /[[:space:]]+/)
          for (i = 1; i <= count; i++) {
            if (entries[i] == "") continue
            eq = index(entries[i], "=")
            if (eq <= 1 || eq == length(entries[i])) {
              fail("staged binding must use table=<decimal count>: " entries[i])
            }
            staged_table = substr(entries[i], 1, eq - 1)
            staged_count = substr(entries[i], eq + 1)
            if (staged_count !~ /^[0-9]+$/) {
              fail("staged count must be a non-negative decimal integer for " staged_table)
            }
            if (staged_header_seen[staged_table]++) {
              fail("duplicate staged-count header for " staged_table)
            }
            print "staged\t" staged_table "\t" staged_count >> headerout
          }
        }

        line = raw
        sub(/[[:space:]]*#.*/, "", line)
        line = trim(line)
        if (line == "") next
        if (line !~ /^\[[^]]+\]/) fail("invalid syntax")

        target = line
        sub(/^\[/, "", target); sub(/\].*/, "", target); target = trim(target)
        rest = line; sub(/^\[[^]]+\]/, "", rest); rest = trim(rest)

        if (rest ~ /^[a-z_]+[.]rows[[:space:]]+/) {
          if (target == "*") fail("row selectors do not support [*]")
          if (!valid[target]) fail("selection table is not preserved: " target)
          rowclass = rest; sub(/[.]rows.*/, "", rowclass); rowclass = cls(rowclass)
          tail = rest; sub(/^[a-z_]+[.]rows[[:space:]]+/, "", tail)
          mode = tail; sub(/[[:space:]]*=.*/, "", mode); mode = tolower(trim(mode))
          if (mode != "include" && mode != "exclude") fail("row selector mode must be include or exclude")
          if (tail !~ /=/) fail("row selector is missing =")
          payload = tail; sub(/^[^=]*=/, "", payload); payload = trim(payload)
          colon = index(payload, ":")
          if (colon < 2) fail("row selector must use id:, row:, or corp:")
          kind = tolower(trim(substr(payload, 1, colon - 1)))
          values = substr(payload, colon + 1)
          if (kind != "id" && kind != "row" && kind != "corp") fail("unsupported row selector kind: " kind)
          if (trim(values) == "") fail("row selector value list is empty")
          value_count = split(values, vals, ",")
          for (j = 1; j <= value_count; j++) {
            value = trim(vals[j])
            if (value == "") fail("row selector contains an empty value")
            from = "\\N"; to = "\\N"; corp = "\\N"; is_range = "f"
            if (kind == "corp") {
              corp = copy_escape(value)
            } else {
              if (value !~ /^[0-9]+(-[0-9]+)?$/) fail(kind " selector must be a non-negative integer or range: " value)
              dash = index(value, "-")
              if (dash > 0) {
                from = substr(value, 1, dash - 1); to = substr(value, dash + 1); is_range = "t"
                if (!decimal_le(from, to)) fail("row selector range is inverted: " value)
              } else {
                from = value; to = value
              }
              if (!decimal_le(from, "9223372036854775807") || !decimal_le(to, "9223372036854775807")) {
                fail(kind " selector exceeds bigint maximum: " value)
              }
            }
            key = target SUBSEP rowclass SUBSEP mode SUBSEP kind SUBSEP value
            if (selector_seen[key]++) {
              printf("warning: selection line %s duplicates selector %s:%s\n", NR, kind, value) > "/dev/stderr"
              continue
            }
            print target "\t" rowclass "\t" mode "\t" kind "\t" from "\t" to "\t" corp "\t" is_range "\t" NR >> rowout
          }
          next
        }

        if (rest !~ /^include[[:space:]]*=/) fail("expected include=classes or <class>.rows include|exclude=<kind>:<values>")
        includes = rest; sub(/^include[[:space:]]*=/, "", includes); includes = trim(includes)
        if (target == "*") wildcard = includes
        else if (!valid[target]) fail("selection table is not preserved: " target)
        else override[target] = includes
      }
      END {
        if (failed) exit 4
        for (i = 1; i <= n; i++) {
          t = order[i]
          includes = (t in override) ? override[t] : wildcard
          part_count = split(includes, parts, ",")
          for (j = 1; j <= part_count; j++) {
            c = cls(parts[j])
            if (c != "" && !seen[t, c]++) print t "\t" c
          }
        }
      }
    ' "$SELECTION_FILE" > "$RUN_DIR/selection_input.tsv" || die4 "invalid selection file: $SELECTION_FILE"
    scope_selection_file_input
    return 0
  fi

  normalize_class_list "${INCLUDE_CLASSES:-new,changed}" "$base_classes" || die4 "invalid --include-classes"
  normalize_class_list "$EXCLUDE_CLASSES" "$exclude_classes" || die4 "invalid --exclude-classes"

  while read -r table; do
    [[ -n "$table" ]] || continue
    while read -r class; do
      [[ -n "$class" ]] || continue
      if ! grep -qx -- "$class" "$exclude_classes"; then
        printf "%s\t%s\n" "$table" "$class" >> "$RUN_DIR/selection_input.tsv"
      fi
    done < "$base_classes"
  done < "$requested"
}

verify_selection_binding() {
  [[ -s "$RUN_DIR/row_selection_input.tsv" ]] || return 0
  local bound_sha table expected actual
  bound_sha="$(awk -F '\t' '$1 == "dump_sha256" { print $2; exit }' "$RUN_DIR/selection_header.tsv")"
  [[ -n "$bound_sha" ]] || die4 "row-selector selection file is missing # dump_sha256=; re-run preview"
  [[ "$bound_sha" = "$DUMP_SHA256" ]] || die4 "selection file was generated from a different dump (expected $DUMP_SHA256, found $bound_sha); re-run preview"

  while read -r table; do
    [[ -n "$table" ]] || continue
    expected="$(awk -F '\t' -v t="$table" '$1 == "staged" && $2 == t { print $3; exit }' "$RUN_DIR/selection_header.tsv")"
    actual="$(awk -F '\t' -v t="$table" '$1 == t && $2 == "STAGED" { print $3; exit }' "$RUN_DIR/stage_counts.tsv")"
    [[ -n "$expected" ]] || die4 "row: selector for $table is missing its # staged $table=<count> binding"
    [[ "$expected" = "${actual:-0}" ]] || die4 "staged row count for $table changed (selection=$expected current=${actual:-0}); re-run preview"
  done < <(awk -F '\t' '$4 == "row" { print $1 }' "$RUN_DIR/row_selection_input.tsv" | sort -u)

  psql_cmd "INSERT INTO delta_ctl.run_metadata(key, value) VALUES
    ('selection_file', $(sql_literal "$SELECTION_FILE")),
    ('selection_bound_sha256', $(sql_literal "$bound_sha"))
    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, created_at = now();" >/dev/null
}

load_selection_tables() {
  build_selection_input
  verify_selection_binding
  psql_cmd "TRUNCATE delta_ctl.selection; TRUNCATE delta_ctl.row_selection; TRUNCATE delta_ctl.selection_diagnostics; TRUNCATE delta_ctl.only_corps;"
  if [[ -s "$RUN_DIR/selection_input.tsv" ]]; then
    "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 \
      -c "COPY delta_ctl.selection(table_name, class) FROM STDIN" \
      < "$RUN_DIR/selection_input.tsv"
  fi
  if [[ -s "$RUN_DIR/row_selection_input.tsv" ]]; then
    if ! "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 \
      -c "COPY delta_ctl.row_selection(table_name, class, mode, kind, value_from, value_to, corp_num, is_range, source_line) FROM STDIN" \
      < "$RUN_DIR/row_selection_input.tsv"; then
      die4 "failed to load row selectors; check selection values and line diagnostics"
    fi
  fi

  if [[ -n "$ONLY_CORPS_FILE" ]]; then
    [[ -r "$ONLY_CORPS_FILE" ]] || die4 "--only-corps file is not readable: $ONLY_CORPS_FILE"
    awk 'NF && $1 !~ /^#/ { print $1 }' "$ONLY_CORPS_FILE" > "$RUN_DIR/only_corps.tsv"
    if [[ -s "$RUN_DIR/only_corps.tsv" ]]; then
      "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 \
        -c "COPY delta_ctl.only_corps(corp_num) FROM STDIN" \
        < "$RUN_DIR/only_corps.tsv"
    fi
  fi
}

prepare_apply_selection() {
  printf "🎯  Loading and stamping selection …\n"
  load_selection_tables
  psql_cmd "SELECT delta_ctl.verify_row_selection();" > "$RUN_DIR/row_selection_validation.out"
  "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 -tA -F $'\t' > "$RUN_DIR/selection_diagnostics.tsv" <<'SQL'
SELECT table_name, class, mode, kind, selector, source_line, COALESCE(matched::text, ''), problem
FROM delta_ctl.selection_diagnostics
ORDER BY source_line, table_name, class;
SQL
  if awk -F '\t' 'NF >= 8 && $8 != "" { found=1 } END { exit !found }' "$RUN_DIR/selection_diagnostics.tsv"; then
    cat "$RUN_DIR/selection_diagnostics.tsv" >&2
    die4 "row selection validation failed; see selection_diagnostics.tsv"
  fi
  psql_cmd "SELECT delta_ctl.stamp_selection();"
  if ! psql_cmd "SELECT delta_ctl.validate_dependencies();" > "$RUN_DIR/selection_validation.out" 2> "$RUN_DIR/selection_validation.err"; then
    cat "$RUN_DIR/selection_validation.err" >&2
    die4 "selection/dependency validation failed"
  fi
  "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 -tA -F $'\t' > "$RUN_DIR/dependency_violations.tsv" <<'SQL'
SELECT child_table, parent_table, reason, row_count, COALESCE(sample_ids, '')
FROM delta_ctl.dependency_violations
ORDER BY child_table, parent_table;
SQL
  if [[ -s "$RUN_DIR/dependency_violations.tsv" ]]; then
    cat "$RUN_DIR/dependency_violations.tsv" >&2
    die4 "selection/dependency validation failed; see dependency_violations.tsv"
  fi

  "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 -tA -F $'\t' > "$RUN_DIR/selected_counts.tsv" <<'SQL'
SELECT table_name, class, row_count, load_phase
FROM delta_ctl.selected_counts()
ORDER BY load_phase, table_name, class;
SQL

  printf "Selected rows:\n"
  if [[ -s "$RUN_DIR/selected_counts.tsv" ]]; then
    awk -F '\t' '{ printf "  %-36s %-20s %s\n", $1, $2, $3 }' "$RUN_DIR/selected_counts.tsv"
  else
    printf "  (none)\n"
  fi
}

confirm_apply() {
  if [[ "$YES" = "true" ]]; then
    return 0
  fi
  printf "Proceed with applying selected rows to %s:%s/%s? Type 'yes' to continue: " "$PGHOST" "$PGPORT" "$PGDATABASE"
  local answer
  read -r answer
  [[ "$answer" = "yes" ]] || die4 "apply cancelled"
}

run_apply_transaction() {
  printf "🚀  Applying selected rows in one transaction …\n"
  set +e
  "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 \
    > "$RUN_DIR/apply_transaction.out" \
    2> "$RUN_DIR/apply_transaction.err" <<SQL
BEGIN ISOLATION LEVEL REPEATABLE READ;
\i $SESSION_BEGIN_SQL
SELECT delta_ctl.run_apply();
COMMIT;
\i $SESSION_END_SQL
SQL
  local status=$?
  set -e
  if [[ "$status" -ne 0 ]]; then
    cat "$RUN_DIR/apply_transaction.err" >&2
    if grep -q "SELECTION_INVALID" "$RUN_DIR/apply_transaction.err"; then
      die4 "selection/dependency validation failed during apply"
    fi
    if grep -q "APPLY_VERIFICATION_FAILED" "$RUN_DIR/apply_transaction.err"; then
      die5 "apply verification failed; transaction was rolled back"
    fi
    die "apply transaction failed; transaction was rolled back"
  fi
}

post_apply_maintenance() {
  printf "🛠  Repairing sequences …\n"
  psql_file "$REPAIR_SEQUENCES_SQL"

  "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 -tA > "$RUN_DIR/touched_tables.txt" <<'SQL'
SELECT table_name FROM delta_ctl.touched_tables ORDER BY table_name;
SQL
  : > "$RUN_DIR/analyze_touched.sql"
  while read -r table; do
    [[ -n "$table" ]] || continue
    printf 'ANALYZE public.%s;\n' "$table" >> "$RUN_DIR/analyze_touched.sql"
  done < "$RUN_DIR/touched_tables.txt"
  if [[ -s "$RUN_DIR/analyze_touched.sql" ]]; then
    printf "📊  Analyzing touched tables …\n"
    psql_file "$RUN_DIR/analyze_touched.sql"
  fi
}

write_apply_summary() {
  local summary="$RUN_DIR/apply_summary.txt"
  {
    printf "Delta restore apply summary\n"
    printf "===========================\n\n"
    printf "Dump: %s\n" "$DUMP"
    printf "Target: %s:%s/%s as %s\n" "$PGHOST" "$PGPORT" "$PGDATABASE" "$PGUSER"
    printf "Run dir: %s\n" "$RUN_DIR"
    printf "Selection source: %s\n" "${SELECTION_FILE:-CLI/default}"
    printf "\n"
  } > "$summary"
  "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 -tA \
    -c "SELECT * FROM delta_ctl.render_apply_summary_lines();" \
    >> "$summary"
  cat "$summary"
}

write_preview_report() {
  local report="$RUN_DIR/preview.txt"
  local detail aligned_detail table_name detail_class rendered total truncated aligned
  {
    printf "Delta restore preview\n"
    printf "=====================\n\n"
    printf "Dump: %s\n" "$DUMP"
    printf "Target: %s:%s/%s as %s\n" "$PGHOST" "$PGPORT" "$PGDATABASE" "$PGUSER"
    printf "Run dir: %s\n" "$RUN_DIR"
    printf "Mode: %s\n" "$MODE"
    printf "Tables: %s\n" "$TABLES_ARG"
    printf "Sample size: %s\n" "$SAMPLE_SIZE"
    printf "Details limit: %s\n" "$DETAILS_LIMIT"
    printf "Selection manifest: %s\n" "$RUN_DIR/selection.conf"
    if [[ -f "$RUN_DIR/dump.manifest.json" ]]; then
      printf "Manifest: %s\n" "$RUN_DIR/dump.manifest.json"
    fi
    printf "\nDetail artifacts\n"
    printf '%s\n' '----------------'
    if [[ -s "$RUN_DIR/detail_artifacts.txt" ]]; then
      while read -r detail; do
        table_name="${detail#details/}"
        table_name="${table_name%.*.tsv}"
        rendered="$(awk 'NR > 1 && $0 !~ /^#/ { count++ } END { print count + 0 }' "$RUN_DIR/$detail")"
        case "$detail" in
          *.new.tsv)
            detail_class="NEW"
            total="$(awk -F '\t' -v t="$table_name" '$1 == t && $2 == "NEW" { n += $3 } END { print n + 0 }' "$RUN_DIR/class_counts.tsv")"
            ;;
          *.changed.tsv)
            detail_class="CHANGED"
            total="$(awk -F '\t' -v t="$table_name" '$1 == t && ($2 == "CHANGED" || $2 == "CHANGED_LOCAL_NEWER") { n += $3 } END { print n + 0 }' "$RUN_DIR/class_counts.tsv")"
            ;;
          *.blocked.tsv)
            detail_class="BLOCKED"
            total="$(awk -F '\t' -v t="$table_name" '$1 == t && ($2 == "BLOCKED_FK" || $2 == "AMBIGUOUS_NK") { n += $3 } END { print n + 0 }' "$RUN_DIR/class_counts.tsv")"
            ;;
        esac

        truncated=""
        if grep -q '^# TRUNCATED at ' "$RUN_DIR/$detail" || [[ "$total" -gt "$DETAILS_LIMIT" ]]; then
          truncated=" (TRUNCATED)"
        fi
        aligned=""
        aligned_detail="${detail%.tsv}.txt"
        if [[ -f "$RUN_DIR/$aligned_detail" ]]; then
          aligned=" · aligned: $aligned_detail"
        fi
        printf -- "- %s — %s of %s %s rows%s%s\n" \
          "$detail" "$rendered" "$total" "$detail_class" "$truncated" "$aligned"
      done < "$RUN_DIR/detail_artifacts.txt"
    else
      printf "(none)\n"
    fi
    cat <<'TIPS'

Viewing tips
------------
Aligned text: open details/<table>.<class>.txt in any editor (turn off word wrap).
Terminal:     column -s $'\t' -t < details/<table>.<class>.tsv | less -S
SQL:          the delta_stage/delta_diff schemas remain installed after preview;
              see "Querying the staged run directly" in README_delta_restore.md.
TIPS
    if [[ -s "$RUN_DIR/drift_local_copy_permitted.tsv" ]]; then
      printf "\nSchema drift warnings\n"
      printf "---------------------\n"
      awk -F '\t' '{ printf "- %s.%s: %s\n", $1, $2, $3 }' "$RUN_DIR/drift_local_copy_permitted.tsv"
    fi
    printf "\n"
  } > "$report"

  cat > "$RUN_DIR/render_preview_lines.sql" <<SQL
SELECT * FROM delta_ctl.render_preview_lines($SAMPLE_SIZE);
SQL
  psql_delta_session_file "$RUN_DIR/render_preview_lines.sql" \
    "$RUN_DIR/preview_lines.out" "$RUN_DIR/preview_lines.err" -tA
  cat "$RUN_DIR/preview_lines.out" >> "$report"

  cat "$report"
}

run_preview_staging() {
  verify_dump_and_manifest
  load_preserved_config
  select_tables
  filter_toc
  install_control_schemas
  create_stage_shells
  stream_stage_data
  create_stage_indexes
  record_stage_counts
  run_preview_classification
  write_row_details
  write_selection_manifest
  write_selection_cookbook
  write_preview_report

  printf '\nNext steps:\n'
  printf '  1. Review %q\n' "$RUN_DIR/preview.txt"
  printf '  2. cp %q my_selection.conf and edit it\n' "$RUN_DIR/selection.conf"
  printf '  3. To validate: %q --dump %q --mode validate' "$0" "$DUMP"
  [[ "$TABLES_ARG" = "all" ]] || printf ' --tables %q' "$TABLES_ARG"
  [[ -z "$INCLUDE_CLASSES" ]] || printf ' --include-classes %q' "$INCLUDE_CLASSES"
  [[ -z "$EXCLUDE_CLASSES" ]] || printf ' --exclude-classes %q' "$EXCLUDE_CLASSES"
  printf ' --selection-file my_selection.conf'
  [[ -z "$ONLY_CORPS_FILE" ]] || printf ' --only-corps %q' "$ONLY_CORPS_FILE"
  printf '\n'
}

verify_resident_run() {
  local resident_state resident_sha

  if ! resident_state="$("$PSQL_BIN" -X $(pg_conn_opts) -qAt -v ON_ERROR_STOP=1 <<'SQL'
SELECT CASE
  WHEN to_regclass('delta_ctl.run_metadata') IS NULL THEN 'NO_RUN'
  WHEN to_regclass('delta_ctl.run_counts') IS NULL
    OR to_regclass('delta_ctl.table_config') IS NULL
    OR to_regclass('delta_ctl.selection') IS NULL
    OR to_regclass('delta_ctl.row_selection') IS NULL
    OR to_regclass('delta_ctl.selection_diagnostics') IS NULL
    OR to_regclass('delta_ctl.only_corps') IS NULL
    OR to_regclass('delta_ctl.dependency_violations') IS NULL
    OR NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'delta_stage')
    OR NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'delta_map')
    OR NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'delta_diff')
    OR to_regprocedure('delta_ctl.verify_row_selection()') IS NULL
    OR to_regprocedure('delta_ctl.stamp_selection()') IS NULL
    OR to_regprocedure('delta_ctl.validate_dependencies()') IS NULL
    OR to_regprocedure('delta_ctl.selected_counts()') IS NULL
    THEN 'INCOMPLETE'
  ELSE 'READY'
END;
SQL
  )"; then
    die2 "could not inspect resident delta run"
  fi

  case "$resident_state" in
    NO_RUN|'') die2 "no resident delta run found; run --mode preview first" ;;
    READY) ;;
    *) die2 "resident delta run is incomplete; re-run preview" ;;
  esac

  compute_dump_sha
  if ! resident_sha="$("$PSQL_BIN" -X $(pg_conn_opts) -qAt -v ON_ERROR_STOP=1 \
      -c "SELECT value FROM delta_ctl.run_metadata WHERE key = 'dump_sha256'")"; then
    die2 "could not read resident delta run metadata"
  fi
  [[ -n "$resident_sha" ]] || die2 "resident delta run has no dump sha256; re-run preview"
  [[ "$resident_sha" = "$DUMP_SHA256" ]] \
    || die2 "resident run was staged from a different dump; re-run preview"

  if ! "$PSQL_BIN" -X $(pg_conn_opts) -v ON_ERROR_STOP=1 -tA -F $'\t' \
      > "$RUN_DIR/stage_counts.tsv" <<'SQL'
SELECT table_name, count_name, row_count
FROM delta_ctl.run_counts
WHERE count_name IN ('STAGED', 'SKIPPED_ABSENT')
ORDER BY table_name, count_name;
SQL
  then
    die2 "could not regenerate staged-count binding from resident run"
  fi
  [[ -s "$RUN_DIR/stage_counts.tsv" ]] \
    || die2 "resident delta run has no staged-count metadata; re-run preview"
}

run_validate_mode() {
  verify_resident_run
  load_preserved_config
  select_tables
  prepare_apply_selection

  printf "✅  Selection is valid.\n"
  printf 'To apply: %q --dump %q --mode apply' "$0" "$DUMP"
  [[ "$TABLES_ARG" = "all" ]] || printf ' --tables %q' "$TABLES_ARG"
  [[ -z "$INCLUDE_CLASSES" ]] || printf ' --include-classes %q' "$INCLUDE_CLASSES"
  [[ -z "$EXCLUDE_CLASSES" ]] || printf ' --exclude-classes %q' "$EXCLUDE_CLASSES"
  [[ -z "$SELECTION_FILE" ]] || printf ' --selection-file %q' "$SELECTION_FILE"
  [[ -z "$ONLY_CORPS_FILE" ]] || printf ' --only-corps %q' "$ONLY_CORPS_FILE"
  printf ' --yes\n'
}

run_apply_mode() {
  verify_dump_and_manifest
  load_preserved_config
  select_tables
  filter_toc
  install_control_schemas
  create_stage_shells
  stream_stage_data
  create_stage_indexes
  record_stage_counts
  run_preview_classification
  write_row_details
  write_selection_manifest
  write_selection_cookbook
  prepare_apply_selection
  confirm_apply
  run_apply_transaction
  post_apply_maintenance
  write_apply_summary
  if [[ "$KEEP_ARTIFACTS" != "true" ]]; then
    cleanup_schemas
  fi
}

##############################################################################
# MAIN
##############################################################################

if [[ "${DELTA_RESTORE_SOURCE_ONLY:-false}" = "true" ]]; then
  return 0 2>/dev/null || exit 0
fi

parse_args "$@"
validate_static_files
init_run_dir
trap on_exit EXIT

acquire_lock

if [[ "$CLEANUP" = "true" ]]; then
  cleanup_schemas
  exit 0
fi

case "$MODE" in
  apply) run_apply_mode ;;
  validate) run_validate_mode ;;
  preview) run_preview_staging ;;
esac
