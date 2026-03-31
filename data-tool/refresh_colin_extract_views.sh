#!/usr/bin/env bash
# refresh_colin_extract_views.sh
#
# Plan / refresh selected COLIN extract materialized views for data-only changes.
#
# Use this when the derived MV definitions have NOT changed and you only need to
# rebuild the affected materialized views in dependency order.
#
# Modes:
#   plan    - print the generated refresh/analyze SQL only (default)
#   refresh - execute the generated refresh/analyze SQL
#
# Notes:
#   - this script refreshes existing materialized views only; it does not create
#     or drop them
#   - use reset_colin_extract_views.sh for MV/view DDL changes
#   - BAR data is now static and should not be treated as a refresh trigger

set -euo pipefail

PSQL_BIN="${PSQL_BIN:-psql}"
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"
PGDATABASE="${PGDATABASE:-colin-mig-corps-test}"
PGSCHEMA="${PGSCHEMA:-public}"
MODE="plan"
TARGETS_CSV="legacy"
SKIP_ANALYZE="false"
LIST_TARGETS="false"

psql_cmd=()
selected_mvs=()
canonical_mv_order=(
  mv_corps_with_officers
  mv_corps_party_role_count
  mv_admin_email_count
  mv_admin_email_domain_count
  mv_addr_issue_counts_by_entity
  mv_addr_quality_by_corp
  mv_addr_quality_screening_by_corp
  mv_share_class_issue_flags
  mv_corp_event_filing_rollup
  mv_legacy_corps_data
  mv_corp_issue_flags
  mv_issue_counts_by_corp_type
)

usage() {
  cat <<'USAGE'
Usage: refresh_colin_extract_views.sh [options]

Options:
  --mode <plan|refresh>      plan=print SQL only (default)
                             refresh=execute generated refresh SQL
  --targets <csv>            comma-separated refresh profiles (default: legacy)
  --skip-analyze             omit ANALYZE statements after refresh
  --list-targets             print the available refresh profiles and exit
  --db, --dbname <name>      target database name (default: colin-mig-corps-test)
  --host <host>              PostgreSQL host (default: localhost)
  --port <port>              PostgreSQL port (default: 5432)
  --user <user>              PostgreSQL user (default: postgres)
  --schema <schema>          target schema (default: public)
  --psql-bin <path>          psql binary to use (default: psql or $PSQL_BIN)
  -h, --help                 show help

Refresh profiles:
  legacy        refresh mv_corp_event_filing_rollup, then mv_legacy_corps_data
                (safe default for legacy-screening data, including rolling two-year counts)
  legacy-direct refresh mv_legacy_corps_data only
                (advanced/leaf-only path when all upstream derived MVs are already current)
  event-filing  alias of legacy; refresh mv_corp_event_filing_rollup,
                then mv_legacy_corps_data
  share         refresh mv_share_class_issue_flags, plus the event rollup,
                then mv_legacy_corps_data
  address       refresh the shared address entity rollup and the legacy-only
                address screening chain: mv_addr_issue_counts_by_entity,
                mv_addr_quality_screening_by_corp, then mv_corp_event_filing_rollup,
                then mv_legacy_corps_data
  address-full  refresh the shared address entity rollup, both address-quality
                layers, the event rollup, legacy MV, and corp issue reporting MVs
  party         refresh the legacy-only corp_party screening chain plus the
                shared address entity rollup: mv_corps_with_officers,
                mv_corps_party_role_count, mv_addr_issue_counts_by_entity,
                mv_addr_quality_screening_by_corp, then mv_corp_event_filing_rollup,
                then mv_legacy_corps_data
  party-full    refresh the corp_party chain, shared address entity rollup,
                both address-quality layers, event rollup, legacy MV,
                and corp issue reporting MVs
  admin-email   refresh mv_admin_email_count, plus the event rollup,
                then mv_legacy_corps_data
  email-domain  refresh mv_admin_email_domain_count only
  corp-issues   refresh mv_addr_issue_counts_by_entity, mv_addr_quality_by_corp,
                mv_corp_issue_flags, then mv_issue_counts_by_corp_type
  all           refresh the full COLIN MV layer in dependency order,
                including the shared address entity rollup

Examples:
  # Preview a safe refresh plan for legacy-screening data
  ./data-tool/refresh_colin_extract_views.sh \
    --targets legacy \
    --db colin-mig-corps-test-subset

  # Refresh event/filing-derived data and then rebuild mv_legacy_corps_data
  ./data-tool/refresh_colin_extract_views.sh \
    --mode refresh \
    --targets event-filing \
    --db colin-mig-corps-test-subset \
    --user postgres

  # Refresh address-driven legacy screening data and issue reporting together
  ./data-tool/refresh_colin_extract_views.sh \
    --mode refresh \
    --targets address-full \
    --db colin-mig-corps-test-subset

Notes:
  - Any profile that refreshes `mv_legacy_corps_data` now refreshes the event/filing rollup first, except `legacy-direct`.
  - `legacy` is the safe/default profile for legacy-screening data.
  - `legacy-direct` is an advanced/leaf-only path that assumes all upstream derived MVs are already current; otherwise `mv_legacy_corps_data` can be refreshed against stale inputs.
  - `event-filing` is kept as an explicit alias of `legacy` for event/filing-driven refreshes.
  - Address-driven profiles now refresh `mv_addr_issue_counts_by_entity` first so the slim and full address-quality MVs share the same upstream rollup.
  - `address` / `party` stop at the slim screening MV for legacy-only refreshes.
  - `address-full` / `party-full` / `corp-issues` continue through `mv_addr_quality_by_corp` for full-wide address issue reporting.
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
}

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
  [[ "$result" == "1" ]]
}

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

quote_ident() {
  local value="$1"
  value="$(printf '%s' "$value" | sed 's/"/""/g')"
  printf '"%s"' "$value"
}

get_relation_kind() {
  local relation_name="$1"
  "${psql_cmd[@]}" -qAt -v "schema_name=$PGSCHEMA" -v "relation_name=$relation_name" <<'SQL'
SELECT COALESCE((
  SELECT c.relkind::text
  FROM pg_class c
  JOIN pg_namespace n
    ON n.oid = c.relnamespace
  WHERE n.nspname = :'schema_name'
    AND c.relname = :'relation_name'
  LIMIT 1
), '');
SQL
}

validate_selected_mvs_exist() {
  local mv_name
  local relkind
  local missing=()
  local wrong_type=()

  for mv_name in "${selected_mvs[@]}"; do
    relkind="$(get_relation_kind "$mv_name")"
    case "$relkind" in
      m)
        ;;
      '')
        missing+=("$mv_name")
        ;;
      *)
        wrong_type+=("$mv_name:$relkind")
        ;;
    esac
  done

  if [[ "${#missing[@]}" -gt 0 || "${#wrong_type[@]}" -gt 0 ]]; then
    local message="selected refresh targets are not available as materialized views in schema '$PGSCHEMA'"
    if [[ "${#missing[@]}" -gt 0 ]]; then
      message+="; missing: ${missing[*]}"
    fi
    if [[ "${#wrong_type[@]}" -gt 0 ]]; then
      message+="; wrong type: ${wrong_type[*]}"
    fi
    die "$message"
  fi
}

contains_item() {
  local needle="$1"
  shift || true
  local item
  for item in "$@"; do
    if [[ "$item" == "$needle" ]]; then
      return 0
    fi
  done
  return 1
}

append_unique_mv() {
  local mv_name="$1"
  if ! contains_item "$mv_name" "${selected_mvs[@]:-}"; then
    selected_mvs+=("$mv_name")
  fi
}

add_all_mvs() {
  selected_mvs=("${canonical_mv_order[@]}")
}

canonicalize_selected_mvs() {
  local requested_mvs=("${selected_mvs[@]}")
  local mv_name

  selected_mvs=()
  for mv_name in "${canonical_mv_order[@]}"; do
    if contains_item "$mv_name" "${requested_mvs[@]}"; then
      selected_mvs+=("$mv_name")
    fi
  done
}

expand_target() {
  local target="$1"
  case "$target" in
    legacy|event-filing)
      append_unique_mv mv_corp_event_filing_rollup
      append_unique_mv mv_legacy_corps_data
      ;;
    legacy-direct)
      append_unique_mv mv_legacy_corps_data
      ;;
    share)
      append_unique_mv mv_share_class_issue_flags
      append_unique_mv mv_corp_event_filing_rollup
      append_unique_mv mv_legacy_corps_data
      ;;
    address)
      append_unique_mv mv_addr_issue_counts_by_entity
      append_unique_mv mv_addr_quality_screening_by_corp
      append_unique_mv mv_corp_event_filing_rollup
      append_unique_mv mv_legacy_corps_data
      ;;
    address-full)
      append_unique_mv mv_addr_issue_counts_by_entity
      append_unique_mv mv_addr_quality_by_corp
      append_unique_mv mv_addr_quality_screening_by_corp
      append_unique_mv mv_corp_event_filing_rollup
      append_unique_mv mv_legacy_corps_data
      append_unique_mv mv_corp_issue_flags
      append_unique_mv mv_issue_counts_by_corp_type
      ;;
    party)
      append_unique_mv mv_corps_with_officers
      append_unique_mv mv_corps_party_role_count
      append_unique_mv mv_addr_issue_counts_by_entity
      append_unique_mv mv_addr_quality_screening_by_corp
      append_unique_mv mv_corp_event_filing_rollup
      append_unique_mv mv_legacy_corps_data
      ;;
    party-full)
      append_unique_mv mv_corps_with_officers
      append_unique_mv mv_corps_party_role_count
      append_unique_mv mv_addr_issue_counts_by_entity
      append_unique_mv mv_addr_quality_by_corp
      append_unique_mv mv_addr_quality_screening_by_corp
      append_unique_mv mv_corp_event_filing_rollup
      append_unique_mv mv_legacy_corps_data
      append_unique_mv mv_corp_issue_flags
      append_unique_mv mv_issue_counts_by_corp_type
      ;;
    admin-email)
      append_unique_mv mv_admin_email_count
      append_unique_mv mv_corp_event_filing_rollup
      append_unique_mv mv_legacy_corps_data
      ;;
    email-domain)
      append_unique_mv mv_admin_email_domain_count
      ;;
    corp-issues)
      append_unique_mv mv_addr_issue_counts_by_entity
      append_unique_mv mv_addr_quality_by_corp
      append_unique_mv mv_corp_issue_flags
      append_unique_mv mv_issue_counts_by_corp_type
      ;;
    all)
      add_all_mvs
      ;;
    *)
      die "invalid refresh profile: $target"
      ;;
  esac
}

resolve_targets() {
  local raw_targets="$1"
  local split_targets=()
  local raw_target
  IFS=',' read -r -a split_targets <<< "$raw_targets"

  selected_mvs=()
  for raw_target in "${split_targets[@]}"; do
    local target
    target="$(trim "$raw_target")"
    [[ -n "$target" ]] || continue
    expand_target "$target"
    if [[ "$target" == "all" ]]; then
      break
    fi
  done

  if [[ "${#selected_mvs[@]}" -eq 0 ]]; then
    die "no refresh profiles were selected"
  fi

  canonicalize_selected_mvs
}

print_targets() {
  cat <<'TARGETS'
Available refresh profiles:
  legacy        -> mv_corp_event_filing_rollup -> mv_legacy_corps_data
  legacy-direct -> mv_legacy_corps_data only (advanced/leaf-only path; assumes upstream MVs are current)
  event-filing  -> alias of legacy
  share         -> mv_share_class_issue_flags -> mv_corp_event_filing_rollup -> mv_legacy_corps_data
  address       -> mv_addr_issue_counts_by_entity -> mv_addr_quality_screening_by_corp -> mv_corp_event_filing_rollup -> mv_legacy_corps_data
  address-full  -> mv_addr_issue_counts_by_entity -> mv_addr_quality_by_corp -> mv_addr_quality_screening_by_corp -> mv_corp_event_filing_rollup -> mv_legacy_corps_data -> mv_corp_issue_flags -> mv_issue_counts_by_corp_type
  party         -> mv_corps_with_officers -> mv_corps_party_role_count -> mv_addr_issue_counts_by_entity -> mv_addr_quality_screening_by_corp -> mv_corp_event_filing_rollup -> mv_legacy_corps_data
  party-full    -> mv_corps_with_officers -> mv_corps_party_role_count -> mv_addr_issue_counts_by_entity -> mv_addr_quality_by_corp -> mv_addr_quality_screening_by_corp -> mv_corp_event_filing_rollup -> mv_legacy_corps_data -> mv_corp_issue_flags -> mv_issue_counts_by_corp_type
  admin-email   -> mv_admin_email_count -> mv_corp_event_filing_rollup -> mv_legacy_corps_data
  email-domain  -> mv_admin_email_domain_count
  corp-issues   -> mv_addr_issue_counts_by_entity -> mv_addr_quality_by_corp -> mv_corp_issue_flags -> mv_issue_counts_by_corp_type
  all           -> full COLIN MV layer in dependency order (including shared address entity rollup)
TARGETS
}

write_plan() {
  local output_file="$1"
  local mv_name
  local quoted_schema
  local quoted_mv

  quoted_schema="$(quote_ident "$PGSCHEMA")"

  {
    printf -- '-- Generated MV refresh plan for %s.%s schema %s\n' "$PGHOST" "$PGDATABASE" "$PGSCHEMA"
    for mv_name in "${selected_mvs[@]}"; do
      quoted_mv="$(quote_ident "$mv_name")"
      printf 'REFRESH MATERIALIZED VIEW %s.%s;\n' "$quoted_schema" "$quoted_mv"
    done

    if [[ "$SKIP_ANALYZE" != "true" ]]; then
      printf '\n'
      for mv_name in "${selected_mvs[@]}"; do
        quoted_mv="$(quote_ident "$mv_name")"
        printf 'ANALYZE %s.%s;\n' "$quoted_schema" "$quoted_mv"
      done
    fi
  } > "$output_file"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="${2:-}"
      shift 2
      ;;
    --targets)
      TARGETS_CSV="${2:-}"
      shift 2
      ;;
    --skip-analyze)
      SKIP_ANALYZE="true"
      shift
      ;;
    --list-targets)
      LIST_TARGETS="true"
      shift
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
  plan|refresh)
    ;;
  *)
    die "invalid mode: $MODE"
    ;;
esac

if [[ "$LIST_TARGETS" == "true" ]]; then
  print_targets
  exit 0
fi

require_command "$PSQL_BIN"
setup_psql_cmd

if ! schema_exists; then
  die "schema '$PGSCHEMA' does not exist in database '$PGDATABASE'"
fi

resolve_targets "$TARGETS_CSV"
validate_selected_mvs_exist

tmp_dir="${TMPDIR:-/tmp}"
tmp_dir="${tmp_dir%/}"
plan_db_slug="${PGDATABASE//[^A-Za-z0-9_.-]/_}"
plan_file="$(mktemp "${tmp_dir}/colin-mv-refresh-plan.${plan_db_slug}.XXXXXX")"
trap 'rm -f "$plan_file"' EXIT

write_plan "$plan_file"

printf 'Generated refresh plan for %s.%s using schema %s:\n' "$PGHOST" "$PGDATABASE" "$PGSCHEMA"
cat "$plan_file"

if [[ "$MODE" == "plan" ]]; then
  exit 0
fi

printf '\nExecuting refresh plan...\n'
# Intentionally do not use a single transaction here so each REFRESH releases
# its stronger locks as soon as it completes.
"${psql_cmd[@]}" -f "$plan_file"
printf 'Done. Selected COLIN materialized views have been refreshed.\n'
