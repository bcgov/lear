#!/usr/bin/env bash
# OCP entrypoint for the COLIN extract delta refresh job.

set -Eeuo pipefail
IFS=$'\n\t'

APP_HOME="${APP_HOME:-/opt/app-root}"
DATA_TOOL_DIR="${DATA_TOOL_DIR:-${APP_HOME}/data-tool}"
APP_DATA="${APP_DATA:-${APP_HOME}/data}"
RUN_ID="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-${HOSTNAME:-local}-$$}"
RUN_DIR="${RUN_DIR:-${APP_DATA}/runs/${RUN_ID}}"
LOG_DIR="${RUN_DIR}/logs"
DBSCHEMA_HOME="${DBSCHEMA_HOME:-${HOME:-${APP_HOME}}/.DbSchema}"
DBSCHEMA_CLI_DIR="${DBSCHEMA_HOME}/cli"
DBSCHEMA_INIT_SQL="${DBSCHEMA_CLI_DIR}/init.sql"
DBSCHEMACLI_CMD="${DBSCHEMACLI_CMD:-dbschemacli}"
DBSCHEMA_SOURCE_CONNECTION="${DBSCHEMA_SOURCE_CONNECTION:-}"
DBSCHEMA_TARGET_CONNECTION="${DBSCHEMA_TARGET_CONNECTION:-}"
DBSCHEMA_TARGET_SCHEMA="${DBSCHEMA_TARGET_SCHEMA:-}"
CLOUDSQL_PROXY_MODE="${CLOUDSQL_PROXY_MODE:-wrapper}"
CLOUDSQL_PROXY_ADDRESS="${CLOUDSQL_PROXY_ADDRESS:-127.0.0.1}"
CLOUDSQL_PROXY_PORT="${CLOUDSQL_PROXY_PORT:-5432}"
CLOUDSQL_PRIVATE_IP="${CLOUDSQL_PRIVATE_IP:-false}"
CLOUDSQL_PROXY_WAIT_SECONDS="${CLOUDSQL_PROXY_WAIT_SECONDS:-60}"
FLOW_MODE="${FLOW_MODE:-refresh}"
FLOW_CHUNK_SIZE="${FLOW_CHUNK_SIZE:-900}"
FLOW_THREADS="${FLOW_THREADS:-4}"
FLOW_MIG_BATCH_ID="${FLOW_MIG_BATCH_ID:-1}"
FLOW_LOOKBACK_HOURS="${FLOW_LOOKBACK_HOURS:-5}"
FLOW_PG_DISABLE_METHOD="${FLOW_PG_DISABLE_METHOD:-table_triggers}"
FLOW_PG_FASTLOAD="${FLOW_PG_FASTLOAD:-false}"
FLOW_INCLUDE_CP="${FLOW_INCLUDE_CP:-false}"
FLOW_INCLUDE_CARS="${FLOW_INCLUDE_CARS:-false}"
FLOW_CORP_FILE="${FLOW_CORP_FILE:-}"
FLOW_RESET_EXTRACT_POSTGRES="${FLOW_RESET_EXTRACT_POSTGRES:-false}"
SMOKE_ONLY="${SMOKE_ONLY:-false}"
RUN_PREFLIGHT="${RUN_PREFLIGHT:-true}"
RUN_POSTFLIGHT="${RUN_POSTFLIGHT:-true}"
SKIP_ORACLE_PREFLIGHT="${SKIP_ORACLE_PREFLIGHT:-false}"
REFRESH_COLIN_EXTRACT_VIEWS="${REFRESH_COLIN_EXTRACT_VIEWS:-false}"
MV_REFRESH_TARGETS="${MV_REFRESH_TARGETS:-legacy}"
MV_REFRESH_SKIP_ANALYZE="${MV_REFRESH_SKIP_ANALYZE:-false}"
PGSCHEMA="${DBSCHEMA_TARGET_SCHEMA}"

CLOUDSQL_PROXY_PID=""
ACTIVE_CHILD_PID=""
ACTIVE_CHILD_GROUP_PID=""
ACTIVE_CHILD_LABEL=""
TERMINATING="false"
TERMINATION_GRACE_SECONDS="${TERMINATION_GRACE_SECONDS:-20}"
CLOUDSQL_PROXY_STOP_SECONDS="${CLOUDSQL_PROXY_STOP_SECONDS:-10}"

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

die() {
  log "ERROR: $*" >&2
  exit 1
}

_send_signal_to_pid_or_group() {
  local signal="$1"
  local pid="$2"
  local group_pid="${3:-}"
  if [[ -n "${group_pid}" ]]; then
    kill "-${signal}" -- "-${group_pid}" >/dev/null 2>&1 || kill "-${signal}" "${pid}" >/dev/null 2>&1 || true
  else
    kill "-${signal}" "${pid}" >/dev/null 2>&1 || true
  fi
}

_wait_for_pid_exit() {
  local pid="$1"
  local timeout_seconds="$2"
  local deadline=$((SECONDS + timeout_seconds))
  while kill -0 "${pid}" >/dev/null 2>&1; do
    if (( SECONDS >= deadline )); then
      return 1
    fi
    sleep 1
  done
  return 0
}

terminate_active_child() {
  local signal="${1:-TERM}"
  local pid="${ACTIVE_CHILD_PID:-}"
  local group_pid="${ACTIVE_CHILD_GROUP_PID:-}"
  local label="${ACTIVE_CHILD_LABEL:-active child}"
  if [[ -z "${pid}" ]] || ! kill -0 "${pid}" >/dev/null 2>&1; then
    return 0
  fi

  if [[ -n "${group_pid}" ]]; then
    log "Forwarding ${signal} to ${label} process group pgid=${group_pid} pid=${pid}"
  else
    log "Forwarding ${signal} to ${label} pid=${pid}"
  fi
  _send_signal_to_pid_or_group "${signal}" "${pid}" "${group_pid}"

  if ! _wait_for_pid_exit "${pid}" "${TERMINATION_GRACE_SECONDS}"; then
    log "${label} did not exit within ${TERMINATION_GRACE_SECONDS}s; sending KILL"
    _send_signal_to_pid_or_group KILL "${pid}" "${group_pid}"
  fi
  wait "${pid}" >/dev/null 2>&1 || true
}

handle_termination() {
  local signal="$1"
  local exit_code=143
  if [[ "${signal}" == "INT" ]]; then
    exit_code=130
  fi
  if [[ "${TERMINATING}" == "true" ]]; then
    return 0
  fi
  TERMINATING="true"
  log "Received ${signal}; terminating active work before cleanup"
  terminate_active_child TERM
  exit "${exit_code}"
}

stop_cloudsql_proxy() {
  if [[ -n "${CLOUDSQL_PROXY_PID}" ]] && kill -0 "${CLOUDSQL_PROXY_PID}" >/dev/null 2>&1; then
    log "Stopping Cloud SQL Auth Proxy pid=${CLOUDSQL_PROXY_PID}"
    kill "${CLOUDSQL_PROXY_PID}" >/dev/null 2>&1 || true
    if ! _wait_for_pid_exit "${CLOUDSQL_PROXY_PID}" "${CLOUDSQL_PROXY_STOP_SECONDS}"; then
      log "Cloud SQL Auth Proxy did not exit within ${CLOUDSQL_PROXY_STOP_SECONDS}s; sending KILL"
      kill -KILL "${CLOUDSQL_PROXY_PID}" >/dev/null 2>&1 || true
    fi
    wait "${CLOUDSQL_PROXY_PID}" >/dev/null 2>&1 || true
    CLOUDSQL_PROXY_PID=""
  fi
}

run_active_command() {
  local label="$1"
  local log_file="$2"
  local workdir="$3"
  shift 3
  local rc=0

  ACTIVE_CHILD_LABEL="${label}"
  if command -v setsid >/dev/null 2>&1; then
    setsid bash -c 'cd "$1" || exit; shift; exec "$@"' bash "${workdir}" "$@" > >(tee "${log_file}") 2>&1 &
    ACTIVE_CHILD_PID=$!
    ACTIVE_CHILD_GROUP_PID="${ACTIVE_CHILD_PID}"
  else
    (cd "${workdir}" && exec "$@") > >(tee "${log_file}") 2>&1 &
    ACTIVE_CHILD_PID=$!
    ACTIVE_CHILD_GROUP_PID=""
  fi

  set +e
  wait "${ACTIVE_CHILD_PID}"
  rc=$?
  set -e

  ACTIVE_CHILD_PID=""
  ACTIVE_CHILD_GROUP_PID=""
  ACTIVE_CHILD_LABEL=""
  return "${rc}"
}

cleanup() {
  local exit_code=$?
  if [[ "${exit_code}" -ne 0 ]]; then
    emit_failure_diagnostics "${exit_code}" || true
  fi
  stop_cloudsql_proxy
  if [[ -f "${DBSCHEMA_INIT_SQL}" ]]; then
    chmod 600 "${DBSCHEMA_INIT_SQL}" >/dev/null 2>&1 || true
  fi
  log "Finished run_id=${RUN_ID} exit_code=${exit_code} artifacts=${RUN_DIR}"
  exit "${exit_code}"
}
trap cleanup EXIT
trap 'handle_termination TERM' TERM
trap 'handle_termination INT' INT

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    die "required environment variable is not set: ${name}"
  fi
}

bool_true() {
  case "${1:-}" in
    true|TRUE|True|1|yes|YES|y|Y) return 0 ;;
    *) return 1 ;;
  esac
}

wait_for_tcp() {
  local host="$1"
  local port="$2"
  local timeout_seconds="$3"
  local deadline=$((SECONDS + timeout_seconds))
  while (( SECONDS < deadline )); do
    if (echo >"/dev/tcp/${host}/${port}") >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

psql_cmd() {
  PGCONNECT_TIMEOUT="${PGCONNECT_TIMEOUT:-10}" \
  PGOPTIONS="${PGOPTIONS:-} -c statement_timeout=${PG_STATEMENT_TIMEOUT_MS:-60000}" \
  PGPASSWORD="${DATABASE_PASSWORD_COLIN_MIGR}" psql \
    -X -v ON_ERROR_STOP=1 \
    -h "${DATABASE_HOST_COLIN_MIGR}" \
    -p "${DATABASE_PORT_COLIN_MIGR}" \
    -U "${DATABASE_USERNAME_COLIN_MIGR}" \
    -d "${DATABASE_NAME_COLIN_MIGR}" \
    "$@"
}

emit_failure_diagnostics() {
  local exit_code="$1"
  mkdir -p "${RUN_DIR}" "${LOG_DIR}" 2>/dev/null || true
  log "Failure diagnostics for run_id=${RUN_ID} exit_code=${exit_code}"
  log "Automatic database recovery is intentionally disabled. Follow the manual recovery steps in jobs/colin-extract-delta/README.md."
  log "Inspect retained artifacts before pod cleanup: ${RUN_DIR}"

  if [[ -f "${LOG_DIR}/refresh-flow.log" ]]; then
    log "Last refresh-flow.log lines:"
    tail -n 80 "${LOG_DIR}/refresh-flow.log" >&2 || true
  fi
  if [[ -f "${LOG_DIR}/cloud-sql-proxy.log" ]]; then
    log "Last cloud-sql-proxy.log lines:"
    tail -n 40 "${LOG_DIR}/cloud-sql-proxy.log" >&2 || true
  fi
  if [[ -f "${LOG_DIR}/dbschema-smoke.log" ]]; then
    log "Last dbschema-smoke.log lines:"
    tail -n 40 "${LOG_DIR}/dbschema-smoke.log" >&2 || true
  fi

  if [[ -n "${DATABASE_HOST_COLIN_MIGR:-}" && -n "${DATABASE_PORT_COLIN_MIGR:-}" && -n "${DATABASE_USERNAME_COLIN_MIGR:-}" && -n "${DATABASE_NAME_COLIN_MIGR:-}" && -n "${DATABASE_PASSWORD_COLIN_MIGR:-}" ]] && command -v psql >/dev/null 2>&1; then
    psql_cmd -v target_schema="${DBSCHEMA_TARGET_SCHEMA}" -qAt >"${RUN_DIR}/failure-disabled-triggers.txt" <<'SQL' || true
SELECT c.relname || ':' || t.tgname || ':' || t.tgenabled
FROM pg_trigger t
JOIN pg_class c ON c.oid = t.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = :'target_schema'
  AND NOT t.tgisinternal
  AND t.tgenabled <> 'O'
ORDER BY c.relname, t.tgname;
SQL
    psql_cmd -v target_schema="${DBSCHEMA_TARGET_SCHEMA}" -qAt >"${RUN_DIR}/failure-helper-counts.txt" <<'SQL' || true
SELECT 'subset_address_stage=' || count(*) FROM :"target_schema".subset_address_stage
UNION ALL SELECT 'subset_excluded_corps=' || count(*) FROM :"target_schema".subset_excluded_corps
UNION ALL SELECT 'subset_excluded_events=' || count(*) FROM :"target_schema".subset_excluded_events
UNION ALL SELECT 'subset_excluded_corp_parties=' || count(*) FROM :"target_schema".subset_excluded_corp_parties;
SQL
    log "Wrote failure diagnostics if DB was reachable: ${RUN_DIR}/failure-disabled-triggers.txt and ${RUN_DIR}/failure-helper-counts.txt"
  fi
}

prepare_runtime() {
  mkdir -p "${RUN_DIR}" "${LOG_DIR}" "${APP_DATA}" "${DBSCHEMA_CLI_DIR}"
  chmod 700 "${RUN_DIR}" "${DBSCHEMA_HOME}" "${DBSCHEMA_CLI_DIR}" 2>/dev/null || true
  export HOME="${HOME:-${APP_HOME}}"
  export PYTHONPATH="${DATA_TOOL_DIR}/flows:${DATA_TOOL_DIR}:${PYTHONPATH:-}"
  export TMPDIR="${RUN_DIR}/tmp"
  mkdir -p "${TMPDIR}"
}

validate_env() {
  require_command bash
  require_command python
  require_command java
  require_command psql
  require_command timeout
  require_command "${DBSCHEMACLI_CMD}"

  require_env DATABASE_USERNAME_COLIN_ORACLE
  require_env DATABASE_PASSWORD_COLIN_ORACLE
  require_env DATABASE_HOST_COLIN_ORACLE
  require_env DATABASE_PORT_COLIN_ORACLE
  require_env DATABASE_NAME_COLIN_ORACLE

  require_env DATABASE_USERNAME_COLIN_MIGR
  require_env DATABASE_PASSWORD_COLIN_MIGR
  require_env DATABASE_NAME_COLIN_MIGR

  case "${CLOUDSQL_PROXY_MODE}" in
    wrapper)
      require_command cloud-sql-proxy
      require_env CLOUDSQL_INSTANCE_CONNECTION_NAME
      ;;
    external|sidecar)
      :
      ;;
    disabled)
      require_env DATABASE_HOST_COLIN_MIGR
      require_env DATABASE_PORT_COLIN_MIGR
      ;;
    *)
      die "CLOUDSQL_PROXY_MODE must be wrapper, external, sidecar, or disabled"
      ;;
  esac

  case "${FLOW_MODE}" in
    refresh|load) : ;;
    *) die "FLOW_MODE must be refresh or load" ;;
  esac

  require_env DBSCHEMA_SOURCE_CONNECTION
  require_env DBSCHEMA_TARGET_CONNECTION
  require_env DBSCHEMA_TARGET_SCHEMA
  validate_dbschema_alias DBSCHEMA_SOURCE_CONNECTION "${DBSCHEMA_SOURCE_CONNECTION}"
  validate_dbschema_alias DBSCHEMA_TARGET_CONNECTION "${DBSCHEMA_TARGET_CONNECTION}"
  validate_dbschema_schema DBSCHEMA_TARGET_SCHEMA "${DBSCHEMA_TARGET_SCHEMA}"
  PGSCHEMA="${DBSCHEMA_TARGET_SCHEMA}"

  if [[ "${FLOW_MODE}" == "load" && -z "${FLOW_CORP_FILE}" ]]; then
    die "FLOW_CORP_FILE is required when FLOW_MODE=load"
  fi
}

start_cloudsql_proxy() {
  if [[ "${CLOUDSQL_PROXY_MODE}" != "wrapper" ]]; then
    log "Cloud SQL proxy mode=${CLOUDSQL_PROXY_MODE}; assuming ${CLOUDSQL_PROXY_ADDRESS}:${CLOUDSQL_PROXY_PORT} is already available"
    return 0
  fi

  local proxy_log="${LOG_DIR}/cloud-sql-proxy.log"
  local proxy_cmd=(
    cloud-sql-proxy
    "--address=${CLOUDSQL_PROXY_ADDRESS}"
    "--port=${CLOUDSQL_PROXY_PORT}"
  )

  if bool_true "${CLOUDSQL_PRIVATE_IP}"; then
    proxy_cmd+=(--private-ip)
  fi
  if [[ -n "${GOOGLE_APPLICATION_CREDENTIALS:-}" && -f "${GOOGLE_APPLICATION_CREDENTIALS}" ]]; then
    proxy_cmd+=("--credentials-file=${GOOGLE_APPLICATION_CREDENTIALS}")
  else
    unset GOOGLE_APPLICATION_CREDENTIALS
  fi
  if [[ -n "${CLOUDSQL_PROXY_EXTRA_ARGS:-}" ]]; then
    local extra_args=()
    local old_ifs="${IFS}"
    IFS=' ' read -r -a extra_args <<< "${CLOUDSQL_PROXY_EXTRA_ARGS}"
    IFS="${old_ifs}"
    proxy_cmd+=("${extra_args[@]}")
  fi
  proxy_cmd+=("${CLOUDSQL_INSTANCE_CONNECTION_NAME}")

  log "Starting Cloud SQL Auth Proxy on ${CLOUDSQL_PROXY_ADDRESS}:${CLOUDSQL_PROXY_PORT}; log=${proxy_log}"
  "${proxy_cmd[@]}" >"${proxy_log}" 2>&1 &
  CLOUDSQL_PROXY_PID=$!

  if ! wait_for_tcp "${CLOUDSQL_PROXY_ADDRESS}" "${CLOUDSQL_PROXY_PORT}" "${CLOUDSQL_PROXY_WAIT_SECONDS}"; then
    tail -n 100 "${proxy_log}" >&2 || true
    die "Cloud SQL Auth Proxy did not become ready on ${CLOUDSQL_PROXY_ADDRESS}:${CLOUDSQL_PROXY_PORT}"
  fi
  log "Cloud SQL Auth Proxy is ready pid=${CLOUDSQL_PROXY_PID}"
}

export_database_env() {
  if [[ "${CLOUDSQL_PROXY_MODE}" == "wrapper" ]]; then
    export DATABASE_HOST_COLIN_MIGR="${CLOUDSQL_PROXY_ADDRESS}"
    export DATABASE_PORT_COLIN_MIGR="${CLOUDSQL_PROXY_PORT}"
  else
    export DATABASE_HOST_COLIN_MIGR="${DATABASE_HOST_COLIN_MIGR:-${CLOUDSQL_PROXY_ADDRESS}}"
    export DATABASE_PORT_COLIN_MIGR="${DATABASE_PORT_COLIN_MIGR:-${CLOUDSQL_PROXY_PORT}}"
  fi
  export PGHOST="${DATABASE_HOST_COLIN_MIGR}"
  export PGPORT="${DATABASE_PORT_COLIN_MIGR}"
  export PGDATABASE="${DATABASE_NAME_COLIN_MIGR}"
  export PGUSER="${DATABASE_USERNAME_COLIN_MIGR}"
  export PGPASSWORD="${DATABASE_PASSWORD_COLIN_MIGR}"
  export PGSCHEMA
}

validate_dbschema_value() {
  local name="$1"
  local value="$2"
  local unsafe_chars=$' \t\r\n;#&|<>$`"'\''\\(){}[]*?!'
  local char reason

  if [[ "${value}" == -* ]]; then
    reason="start with '-' because DbSchemaCLI may parse it as another option"
  elif [[ "${value}" == *--* ]]; then
    reason="contain '--' because unquoted DbSchemaCLI init.sql values must not contain comment-like tokens"
  else
    for (( i=0; i<${#unsafe_chars}; i++ )); do
      char="${unsafe_chars:i:1}"
      if [[ "${value}" == *"${char}"* ]]; then
        case "${char}" in
          $' ' | $'\t' | $'\r' | $'\n') reason="contain whitespace or line breaks" ;;
          *) reason="contain reserved character '${char}'" ;;
        esac
        break
      fi
    done
  fi

  if [[ -n "${reason:-}" ]]; then
    if [[ "${name}" == *PASSWORD* ]]; then
      die "${name} cannot be used by this job because DbSchemaCLI init.sql connection lines are unquoted and the value must not ${reason}. Rotate/update the secret to avoid shell/DbSchema metacharacters before running this job."
    fi
    die "${name} cannot ${reason}; DbSchemaCLI init.sql connection values are written unquoted by this job."
  fi
}

validate_dbschema_alias() {
  local name="$1"
  local value="$2"
  if [[ ! "${value}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    die "${name} must be a conservative DbSchema identifier using letters, digits, and underscore, and must not start with a digit"
  fi
}

validate_dbschema_schema() {
  local name="$1"
  local value="$2"
  if [[ ! "${value}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    die "${name} must be a conservative Postgres schema identifier using letters, digits, and underscore, and must not start with a digit"
  fi
  if [[ "${value}" =~ [A-Z] ]]; then
    die "${name} must be lowercase; PostgreSQL folds unquoted uppercase identifiers to lowercase, so uppercase schema values are rejected to avoid mismatches"
  fi
}

generate_dbschema_init() {
  log "Generating DbSchemaCLI init at ${DBSCHEMA_INIT_SQL}"
  validate_dbschema_value DATABASE_USERNAME_COLIN_ORACLE "${DATABASE_USERNAME_COLIN_ORACLE}"
  validate_dbschema_value DATABASE_PASSWORD_COLIN_ORACLE "${DATABASE_PASSWORD_COLIN_ORACLE}"
  validate_dbschema_value DATABASE_HOST_COLIN_ORACLE "${DATABASE_HOST_COLIN_ORACLE}"
  validate_dbschema_value DATABASE_PORT_COLIN_ORACLE "${DATABASE_PORT_COLIN_ORACLE}"
  validate_dbschema_value DATABASE_NAME_COLIN_ORACLE "${DATABASE_NAME_COLIN_ORACLE}"
  validate_dbschema_value DATABASE_USERNAME_COLIN_MIGR "${DATABASE_USERNAME_COLIN_MIGR}"
  validate_dbschema_value DATABASE_PASSWORD_COLIN_MIGR "${DATABASE_PASSWORD_COLIN_MIGR}"
  validate_dbschema_value DATABASE_HOST_COLIN_MIGR "${DATABASE_HOST_COLIN_MIGR}"
  validate_dbschema_value DATABASE_PORT_COLIN_MIGR "${DATABASE_PORT_COLIN_MIGR}"
  validate_dbschema_value DATABASE_NAME_COLIN_MIGR "${DATABASE_NAME_COLIN_MIGR}"
  validate_dbschema_value DBSCHEMA_SOURCE_CONNECTION "${DBSCHEMA_SOURCE_CONNECTION}"
  validate_dbschema_value DBSCHEMA_TARGET_CONNECTION "${DBSCHEMA_TARGET_CONNECTION}"
  validate_dbschema_value DBSCHEMA_TARGET_SCHEMA "${DBSCHEMA_TARGET_SCHEMA}"
  validate_dbschema_alias DBSCHEMA_SOURCE_CONNECTION "${DBSCHEMA_SOURCE_CONNECTION}"
  validate_dbschema_alias DBSCHEMA_TARGET_CONNECTION "${DBSCHEMA_TARGET_CONNECTION}"
  validate_dbschema_schema DBSCHEMA_TARGET_SCHEMA "${DBSCHEMA_TARGET_SCHEMA}"
  mkdir -p "${DBSCHEMA_HOME}/drivers/PostgreSql" "${DBSCHEMA_HOME}/drivers/Oracle"
  if [[ -d "${DBSCHEMA_DRIVER_DIR:-}" ]]; then
    cp -R "${DBSCHEMA_DRIVER_DIR}/." "${DBSCHEMA_HOME}/drivers/" 2>/dev/null || true
  fi

  umask 077
  cat >"${DBSCHEMA_INIT_SQL}" <<EOF_INIT
register driver Oracle oracle.jdbc.OracleDriver jdbc:oracle:thin:@{HOST}:{PORT}:{DB} "port=1521"
connection ${DBSCHEMA_SOURCE_CONNECTION} -d Oracle -u ${DATABASE_USERNAME_COLIN_ORACLE} -p ${DATABASE_PASSWORD_COLIN_ORACLE} -h ${DATABASE_HOST_COLIN_ORACLE} -P ${DATABASE_PORT_COLIN_ORACLE} -D ${DATABASE_NAME_COLIN_ORACLE}
register driver PostgreSql org.postgresql.Driver jdbc:postgresql://{HOST}:{PORT}/{DB} "port=5432"
connection ${DBSCHEMA_TARGET_CONNECTION} -d PostgreSql -u ${DATABASE_USERNAME_COLIN_MIGR} -p ${DATABASE_PASSWORD_COLIN_MIGR} -h ${DATABASE_HOST_COLIN_MIGR} -P ${DATABASE_PORT_COLIN_MIGR} -D ${DATABASE_NAME_COLIN_MIGR}
EOF_INIT
  chmod 600 "${DBSCHEMA_INIT_SQL}"
}

print_versions() {
  log "run_id=${RUN_ID} artifacts=${RUN_DIR}"
  log "python=$(python --version 2>&1)"
  log "java=$(java -version 2>&1 | head -n 1)"
  log "psql=$(psql --version 2>&1)"
  log "dbschemacli=$(command -v "${DBSCHEMACLI_CMD}")"
  python - <<'PY'
import oracledb
print(f"oracledb={oracledb.__version__}")
PY
  if command -v cloud-sql-proxy >/dev/null 2>&1; then
    log "cloud-sql-proxy=$(cloud-sql-proxy --version 2>&1 | head -n 1)"
  fi
  log "options mode=${FLOW_MODE} chunk_size=${FLOW_CHUNK_SIZE} threads=${FLOW_THREADS} mig_batch_id=${FLOW_MIG_BATCH_ID} lookback_hours=${FLOW_LOOKBACK_HOURS} include_cars=${FLOW_INCLUDE_CARS} reset_extract_postgres=${FLOW_RESET_EXTRACT_POSTGRES} refresh_mvs=${REFRESH_COLIN_EXTRACT_VIEWS} mv_targets=${MV_REFRESH_TARGETS} source_connection=${DBSCHEMA_SOURCE_CONNECTION} target_connection=${DBSCHEMA_TARGET_CONNECTION} target_schema=${DBSCHEMA_TARGET_SCHEMA}"
}

run_dbschema_smoke() {
  local smoke_sql="${RUN_DIR}/dbschema-smoke.sql"
  local smoke_log="${LOG_DIR}/dbschema-smoke.log"

  cat >"${smoke_sql}" <<EOF_SMOKE
vset cli.settings.ignore_errors=false
connect ${DBSCHEMA_TARGET_CONNECTION};
learn schema ${DBSCHEMA_TARGET_SCHEMA};
select 1;
connect ${DBSCHEMA_SOURCE_CONNECTION};
select 1 from dual;
EOF_SMOKE

  log "Running DbSchemaCLI smoke checks for target=${DBSCHEMA_TARGET_CONNECTION} source=${DBSCHEMA_SOURCE_CONNECTION}; log=${smoke_log}"
  run_active_command "DbSchemaCLI smoke" "${smoke_log}" "${APP_HOME}" timeout 60 "${DBSCHEMACLI_CMD}" "${smoke_sql}" \
    || die "DbSchemaCLI smoke failed; see ${smoke_log}"
}

preflight_checks() {
  bool_true "${RUN_PREFLIGHT}" || return 0
  log "Running preflight checks"
  wait_for_tcp "${DATABASE_HOST_COLIN_MIGR}" "${DATABASE_PORT_COLIN_MIGR}" 10 \
    || die "Postgres TCP endpoint is not reachable"
  psql_cmd -qAt -c "SELECT 1;" >/dev/null
  local helper_table_count
  helper_table_count="$(psql_cmd -v target_schema="${DBSCHEMA_TARGET_SCHEMA}" -qAt <<'SQL'
WITH required(relname) AS (
  VALUES
    ('subset_address_stage'),
    ('subset_excluded_corps'),
    ('subset_excluded_events'),
    ('subset_excluded_corp_parties'),
    ('colin_extract_version')
)
SELECT count(*)
FROM required
WHERE to_regclass(format('%I.%I', :'target_schema', relname)) IS NOT NULL;
SQL
)"
  [[ "${helper_table_count}" == "5" ]] || die "missing required COLIN extract helper table(s); apply latest colin_corps_extract_postgres_ddl"

  if bool_true "${REFRESH_COLIN_EXTRACT_VIEWS}"; then
    "${DATA_TOOL_DIR}/refresh_colin_extract_views.sh" \
      --mode plan \
      --targets "${MV_REFRESH_TARGETS}" \
      --db "${DATABASE_NAME_COLIN_MIGR}" \
      --host "${DATABASE_HOST_COLIN_MIGR}" \
      --port "${DATABASE_PORT_COLIN_MIGR}" \
      --user "${DATABASE_USERNAME_COLIN_MIGR}" \
      --schema "${PGSCHEMA}" \
      >"${RUN_DIR}/mv-refresh-plan.preflight.sql"
  fi

  if [[ "${SKIP_ORACLE_PREFLIGHT}" != "true" ]]; then
    (cd "${DATA_TOOL_DIR}/flows" && python - <<'PY')
from common.init_utils import colin_oracle_init, get_config
engine = colin_oracle_init.fn(get_config.fn())
engine.dispose()
PY
  fi
  run_dbschema_smoke
  test -w "${RUN_DIR}" || die "artifact directory is not writable: ${RUN_DIR}"
  log "Preflight checks passed"
}

run_refresh_flow() {
  local master_script="${RUN_DIR}/subset_${FLOW_MODE}.sql"
  local argv=(
    python
    "${DATA_TOOL_DIR}/flows/refresh_extract_subset_flow.py"
    --mode "${FLOW_MODE}"
    --chunk-size "${FLOW_CHUNK_SIZE}"
    --threads "${FLOW_THREADS}"
    --pg-disable-method "${FLOW_PG_DISABLE_METHOD}"
    --artifact-dir "${RUN_DIR}"
    --out "${master_script}"
    --run-dbschemacli
    --dbschemacli-cmd "${DBSCHEMACLI_CMD}"
    --source-connection "${DBSCHEMA_SOURCE_CONNECTION}"
    --target-connection "${DBSCHEMA_TARGET_CONNECTION}"
    --target-schema "${DBSCHEMA_TARGET_SCHEMA}"
    --mig-batch-id "${FLOW_MIG_BATCH_ID}"
    --lookback-hours "${FLOW_LOOKBACK_HOURS}"
  )

  if [[ -n "${FLOW_CORP_FILE}" ]]; then
    argv+=(--corp-file "${FLOW_CORP_FILE}")
  fi
  if bool_true "${FLOW_PG_FASTLOAD}"; then
    argv+=(--pg-fastload)
  fi
  if bool_true "${FLOW_INCLUDE_CP}"; then
    argv+=(--include-cp)
  fi
  if bool_true "${FLOW_INCLUDE_CARS}"; then
    argv+=(--include-cars)
  else
    argv+=(--no-cars)
  fi
  if ! bool_true "${FLOW_RESET_EXTRACT_POSTGRES}"; then
    argv+=(--no-reset-extract-postgres)
  fi

  log "Running refresh_extract_subset_flow.py; generated master=${master_script}"
  run_active_command "refresh_extract_subset_flow.py" "${LOG_DIR}/refresh-flow.log" "${APP_HOME}" "${argv[@]}"
}

refresh_materialized_views() {
  bool_true "${REFRESH_COLIN_EXTRACT_VIEWS}" || return 0
  local argv=(
    "${DATA_TOOL_DIR}/refresh_colin_extract_views.sh"
    --mode refresh
    --targets "${MV_REFRESH_TARGETS}"
    --db "${DATABASE_NAME_COLIN_MIGR}"
    --host "${DATABASE_HOST_COLIN_MIGR}"
    --port "${DATABASE_PORT_COLIN_MIGR}"
    --user "${DATABASE_USERNAME_COLIN_MIGR}"
    --schema "${PGSCHEMA}"
  )
  if bool_true "${MV_REFRESH_SKIP_ANALYZE}"; then
    argv+=(--skip-analyze)
  fi
  log "Refreshing COLIN extract materialized views targets=${MV_REFRESH_TARGETS}"
  run_active_command "refresh_colin_extract_views.sh" "${LOG_DIR}/mv-refresh.log" "${APP_HOME}" "${argv[@]}"
}

postflight_checks() {
  bool_true "${RUN_POSTFLIGHT}" || return 0
  log "Running postflight checks"
  local disabled_triggers
  disabled_triggers="$(psql_cmd -v target_schema="${DBSCHEMA_TARGET_SCHEMA}" -qAt <<'SQL'
SELECT c.relname || ':' || t.tgname || ':' || t.tgenabled
FROM pg_trigger t
JOIN pg_class c ON c.oid = t.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = :'target_schema'
  AND NOT t.tgisinternal
  AND c.relname = ANY (ARRAY[
    'corporation','corp_name','corp_state','event','filing','filing_user','office','corp_comments',
    'ledger_text','corp_party','corp_party_relationship','offices_held','completing_party','submitting_party',
    'corp_flag','cont_out','conv_event','conv_ledger','corp_involved_amalgamating','corp_involved_cont_in',
    'corp_restriction','correction','jurisdiction','resolution','share_series','share_struct','share_struct_cls',
    'notification','notification_resend','party_notification','payment','carsfile','carsbox','carsrept','carindiv',
    'corp_processing','auth_processing','affiliation_processing','colin_tracking'
  ])
  AND t.tgenabled <> 'O';
SQL
)"
  if [[ -n "${disabled_triggers}" ]]; then
    printf '%s\n' "${disabled_triggers}" >"${RUN_DIR}/postflight-disabled-triggers.txt"
    die "postflight found non-origin trigger state; see ${RUN_DIR}/postflight-disabled-triggers.txt"
  fi

  local helper_counts
  helper_counts="$(psql_cmd -v target_schema="${DBSCHEMA_TARGET_SCHEMA}" -qAt <<'SQL'
SELECT 'subset_address_stage=' || count(*) FROM :"target_schema".subset_address_stage
UNION ALL SELECT 'subset_excluded_corps=' || count(*) FROM :"target_schema".subset_excluded_corps
UNION ALL SELECT 'subset_excluded_events=' || count(*) FROM :"target_schema".subset_excluded_events
UNION ALL SELECT 'subset_excluded_corp_parties=' || count(*) FROM :"target_schema".subset_excluded_corp_parties;
SQL
)"
  printf '%s\n' "${helper_counts}" >"${RUN_DIR}/postflight-helper-counts.txt"
  if printf '%s\n' "${helper_counts}" | grep -v '=0$' >/dev/null 2>&1; then
    die "postflight found non-empty helper tables; see ${RUN_DIR}/postflight-helper-counts.txt"
  fi
  log "Postflight checks passed"
}

main() {
  prepare_runtime
  validate_env
  export_database_env
  start_cloudsql_proxy
  generate_dbschema_init
  print_versions
  preflight_checks

  if bool_true "${SMOKE_ONLY}"; then
    log "SMOKE_ONLY=true; exiting after successful preflight"
    return 0
  fi

  run_refresh_flow
  refresh_materialized_views
  postflight_checks
  log "COLIN extract delta run completed successfully"
}

main "$@"
