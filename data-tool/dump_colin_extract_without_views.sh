#!/usr/bin/env bash
# dump_colin_extract_without_views.sh
#
# Dumps the COLIN extract database while excluding the derived view/materialized-view layer.

set -euo pipefail

##############################################################################
# USER-TUNABLE PARAMETERS
##############################################################################

# -- Runtime mode --------------------------------------------------------------
MODE="${MODE:-dump}"                   # dump | print
PG_DUMP_BIN="${PG_DUMP_BIN:-pg_dump}"

# -- Connection ----------------------------------------------------------------
PGHOST="${PGHOST:-localhost}"          # or --host
PGPORT="${PGPORT:-5432}"               # or --port
PGUSER="${PGUSER:-postgres}"           # or --user
PGDATABASE="${PGDATABASE:-colin-mig-corps-test}" # or --dbname
PGSCHEMA="${PGSCHEMA:-public}"
# Supply the password *either* via a .pgpass file *or* one-shot:
#   PGPASSWORD=secret MODE=dump ./dump_colin_extract_without_views.sh
##############################################################################

# -- Runtime options -----------------------------------------------------------
BACKUP_DIR="${BACKUP_DIR:-.}"
if [[ -z "${DUMP:-}" ]]; then
  DUMP="${BACKUP_DIR}/pg_colin_mig_corps_${PGDATABASE}_no_views_$(date +%Y%m%d).tar"
fi

##############################################################################
# INTERNAL HELPERS
##############################################################################

die() { printf >&2 "error: %s\n" "$*"; exit 1; }

print_command() {
  local i
  for i in "${!CMD[@]}"; do
    if [[ "$i" -eq 0 ]]; then
      printf '  %q' "${CMD[$i]}"
    else
      printf ' \\\n    %q' "${CMD[$i]}"
    fi
  done
  printf '\n'
}

##############################################################################
# DERIVED VIEW/MV EXCLUSIONS
##############################################################################

# Intentionally duplicated from data-tool/scripts/colin_corps_extract_generate_view_drop.sql.
# Keep this list synchronized with that canonical allowlist.
EXCLUDED_OBJECTS=(
  v_addr_links
  v_addr_issues
  v_auth_component_operation_audit
  v_business_state
  v_corp_issue_flags_long
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

case "$MODE" in
  print|dump) ;;
  *) die "MODE must be 'print' or 'dump'" ;;
esac

CMD=(
  "$PG_DUMP_BIN"
  -F t
  -b
  -v
  --no-owner
  --no-acl
  -h "$PGHOST"
  -p "$PGPORT"
  -U "$PGUSER"
  -d "$PGDATABASE"
)

for object in "${EXCLUDED_OBJECTS[@]}"; do
  CMD+=("--exclude-table=${PGSCHEMA}.${object}")
done

CMD+=(-f "$DUMP")

printf "📦  COLIN extract dump without derived views/materialized views\n"
printf "Mode: %s\n" "$MODE"
printf "Database: %s@%s:%s/%s\n" "$PGUSER" "$PGHOST" "$PGPORT" "$PGDATABASE"
printf "Schema: %s\n" "$PGSCHEMA"
printf "Output: %s\n" "$DUMP"
printf "Excluded objects:\n"
for object in "${EXCLUDED_OBJECTS[@]}"; do
  printf "  - %s.%s\n" "$PGSCHEMA" "$object"
done
printf "Command:\n"
print_command

if [[ "$MODE" == "print" ]]; then
  printf "\nPrint mode only; no output directory created and pg_dump was not run.\n"
  exit 0
fi

mkdir -p "$(dirname "$DUMP")"
printf "\nRunning pg_dump...\n"
"${CMD[@]}"
printf "✅  Dump written to %s\n" "$DUMP"
