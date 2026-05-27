# COLIN Extract Delta Job

OCP CronJob wrapper for the existing `data-tool/flows/refresh_extract_subset_flow.py` refresh/subset workflow. This package does **not** replace the data-tool generator; it packages the runtime, starts optional Cloud SQL Auth Proxy, generates DbSchemaCLI connections, runs the flow with explicit CLI arguments, and retains run artifacts for recovery.

## What this job does

1. Creates `/opt/app-root/data/runs/<run-id>` for non-secret artifacts.
2. Optionally starts Cloud SQL Auth Proxy on `127.0.0.1:$CLOUDSQL_PROXY_PORT`.
3. Exports the Postgres env used by Python, `psql`, and DbSchema target connection.
4. Generates credential-bearing `~/.DbSchema/cli/init.sql` outside retained run artifacts with explicit rollout inputs for:
   - source Oracle connection `${DBSCHEMA_SOURCE_CONNECTION}`,
   - target Postgres connection `${DBSCHEMA_TARGET_CONNECTION}`, and
   - target Postgres schema `${DBSCHEMA_TARGET_SCHEMA}`.
5. Runs smoke/preflight checks, including non-mutating DbSchemaCLI connect/select checks for both generated aliases and `learn schema ${DBSCHEMA_TARGET_SCHEMA}`.
6. Invokes `refresh_extract_subset_flow.py` as a standalone script with explicit source alias, target alias, and target schema args.
7. Optionally refreshes materialized views using `data-tool/refresh_colin_extract_views.sh --schema ${DBSCHEMA_TARGET_SCHEMA}`.
8. Runs postflight checks for trigger state and helper table cleanup in `${DBSCHEMA_TARGET_SCHEMA}`.

## Build

Builds must use the repository root as Docker context:

```bash
docker build --platform linux/amd64 -f jobs/colin-extract-delta/Dockerfile -t colin-extract-delta:dev . \
  --build-arg DBSCHEMA_SHA256=<sha256> \
  --build-arg ORACLE_IC_SHA256=<sha256> \
  --build-arg POSTGRES_JDBC_SHA256=<sha256> \
  --build-arg ORACLE_JDBC_SHA256=<sha256> \
  --build-arg CLOUD_SQL_PROXY_SHA256=<sha256>
# or export those checksum variables first, then:
make -C jobs/colin-extract-delta build
```

Runtime image assumptions:

- Python dependencies come from `data-tool/requirements.txt`, plus the data-tool install-contract packages `legal_api`, `registry_schemas`, and `sql-versioning`.
- Oracle Instant Client Basic Lite is installed because `data-tool` enables `python-oracledb` thick mode.
- Java, PostgreSQL client tools, DbSchemaCLI 9.7.1, Oracle/Postgres JDBC jars, and Cloud SQL Auth Proxy v2 are installed in the image.
- DbSchemaCLI is installed from the standard DbSchema archive and used as a command-line client through the free CLI path. No DbSchema license key is required or wired into the OCP job.
- CI/local builds must pass SHA256 build args (`DBSCHEMA_SHA256`, `ORACLE_IC_SHA256`, `POSTGRES_JDBC_SHA256`, `ORACLE_JDBC_SHA256`, `CLOUD_SQL_PROXY_SHA256`). The Dockerfile fails closed if any external binary/JAR checksum is missing.

## Required secrets/env

Secret `${NAME}-${TAG}-secret` should provide:

| Key | Purpose |
|---|---|
| `DATABASE_USERNAME_COLIN_MIGR` | Cloud SQL/Postgres target user |
| `DATABASE_PASSWORD_COLIN_MIGR` | Cloud SQL/Postgres target password |
| `DATABASE_NAME_COLIN_MIGR` | Cloud SQL/Postgres target DB |
| `DATABASE_USERNAME_COLIN_ORACLE` | Oracle source user |
| `DATABASE_PASSWORD_COLIN_ORACLE` | Oracle source password |
| `DATABASE_HOST_COLIN_ORACLE` | Oracle host |
| `DATABASE_PORT_COLIN_ORACLE` | Oracle port, usually `1521` |
| `DATABASE_NAME_COLIN_ORACLE` | Oracle service/database name |
| `CLOUDSQL_INSTANCE_CONNECTION_NAME` | Required for `CLOUDSQL_PROXY_MODE=wrapper` |
| `DATABASE_HOST_COLIN_MIGR` | Optional; required only for `CLOUDSQL_PROXY_MODE=disabled` direct networking |
| `DATABASE_PORT_COLIN_MIGR` | Optional; required only for `CLOUDSQL_PROXY_MODE=disabled` direct networking |

Optional JSON-key proxy mode mounts secret `${GCP_SA_SECRET_NAME}` key `${GCP_SA_SECRET_KEY}` at `/var/secrets/google/cloudsql-service-account.json` and sets `GOOGLE_APPLICATION_CREDENTIALS`. The OpenShift template requires these values to be supplied explicitly; if the optional file is absent, `run.sh` unsets `GOOGLE_APPLICATION_CREDENTIALS` so Workload Identity/ambient ADC can be used if validated.

Required OpenShift rollout parameters with no concrete defaults:

| Parameter | Purpose |
|---|---|
| `TAG` | Environment/resource suffix, supplied per deployment. |
| `IMAGE_NAMESPACE` | Namespace containing the externally built image. |
| `IMAGE_TAG` | Image tag to deploy. |
| `DBSCHEMA_SOURCE_CONNECTION` | Source Oracle alias generated in `init.sql` and rendered into generated transfer SQL. |
| `DBSCHEMA_TARGET_CONNECTION` | Target Postgres alias generated in `init.sql` and passed through the flow/generator. |
| `DBSCHEMA_TARGET_SCHEMA` | Target Postgres schema rendered into generated helper/transfer SQL and used as `PGSCHEMA`. |
| `GCP_SA_SECRET_NAME` / `GCP_SA_SECRET_KEY` | JSON-key secret values when JSON-key Cloud SQL proxy mode is used; supply explicit deployment values even if ambient ADC is validated and the optional volume is unused. |

DbSchema init generation writes the direct OCP secrets into runtime `~/.DbSchema/cli/init.sql` using DbSchemaCLI connection text syntax. This file is credential-bearing, is created under a restrictive umask, must remain `0600`, and must stay outside retained run artifacts. Because this job does not implement reliable DbSchema init escaping, connection values reject whitespace/line breaks, semicolons, comment-like `#`/`--`, leading `-`, and shell/DbSchema metacharacters such as quotes, backslashes, `$`, `` ` ``, `&`, `|`, redirection, brackets/braces/parentheses, globs, and `!`; database passwords with those characters must be rotated/updated before this job can run. Alias names are restricted to conservative DbSchema identifiers. The target schema is restricted to a lowercase conservative PostgreSQL identifier to avoid unquoted uppercase/lowercase folding mismatches. The configured source alias is rendered into transfer SQL, and the configured target schema is rendered into helper/transfer SQL.

## Important runtime knobs

| Env | Default | Notes |
|---|---:|---|
| `SMOKE_ONLY` | `false` | `true` runs preflight only and exits before data movement. |
| `CLOUDSQL_PROXY_MODE` | `wrapper` | `wrapper`, `external`, `sidecar`, or `disabled`. Wrapper mode starts/cleans up proxy in `run.sh` and forces target DB host/port to the local proxy address/port. |
| `FLOW_MODE` | `refresh` | Scheduled job should use `refresh`. `load` requires `FLOW_CORP_FILE`. |
| `FLOW_CORP_FILE` | unset | Optional in refresh mode to replay a retained/curated feed; required in load mode. |
| `FLOW_RESET_EXTRACT_POSTGRES` | `false` | Explicit destructive DB reset for load mode only when approved. |
| `FLOW_MIG_BATCH_ID` | `1` | Passed to data-tool CLI. |
| `FLOW_LOOKBACK_HOURS` | `5` | Rolling v1 lookback. Not a durable high-watermark. |
| `FLOW_INCLUDE_CARS` | `false` | Keep false unless the global cars* truncate/reload is explicitly approved. |
| `REFRESH_COLIN_EXTRACT_VIEWS` | `false` | Optional whole-MV refresh after DbSchema transfer. |
| `MV_REFRESH_TARGETS` | `legacy` | First supported MV profile. |
| `TERMINATION_GRACE_SECONDS` | `20` | Seconds to wait for the active DbSchema/flow/MV child after `TERM`/`INT` before sending `KILL`. |
| `CLOUDSQL_PROXY_STOP_SECONDS` | `10` | Seconds to wait for the wrapper-started Cloud SQL Auth Proxy during cleanup before sending `KILL`. |
| `PGCONNECT_TIMEOUT` | `10` | libpq connect timeout used by wrapper `psql` preflight/postflight/diagnostic queries. |
| `PG_STATEMENT_TIMEOUT_MS` | `60000` | Postgres statement timeout used by wrapper `psql` preflight/postflight/diagnostic queries. |
| `DBSCHEMA_SOURCE_CONNECTION` | required in OCP/run.sh | Must match the source alias generated in runtime `init.sql` and rendered into transfer SQL. Direct/local data-tool generator defaults are compatibility defaults only and must not be relied on by OCP. |
| `DBSCHEMA_TARGET_CONNECTION` | required in OCP/run.sh | Must match the target alias generated in runtime `init.sql` and emitted by the flow/generator. Direct/local data-tool flow/generator defaults are compatibility defaults only and must not be relied on by OCP. |
| `DBSCHEMA_TARGET_SCHEMA` | required in OCP/run.sh | Lowercase target Postgres schema rendered into helper/transfer SQL and used to derive `PGSCHEMA`. Direct/local generator defaults are compatibility defaults only and must not be relied on by OCP. |

## Local smoke

With an env file containing the required values:

```bash
make -C jobs/colin-extract-delta build
docker run --rm --env-file jobs/colin-extract-delta/.env \
  -e SMOKE_ONLY=true \
  colin-extract-delta:dev
```

This validates tools, proxy, target Postgres connection/helper tables in `${DBSCHEMA_TARGET_SCHEMA}`, Oracle connection, DbSchemaCLI startup, and both generated DbSchema aliases by running `connect`, `learn schema ${DBSCHEMA_TARGET_SCHEMA}`, and trivial `select` statements against target `${DBSCHEMA_TARGET_CONNECTION}` and source `${DBSCHEMA_SOURCE_CONNECTION}`. It does not run transfers or move data.

## OCP smoke

1. Process/apply the ImageStream template in tools.
2. Push the externally built image to `${IMAGE_NAMESPACE}/${NAME}:${IMAGE_TAG}`.
3. Process/apply the CronJob template with `SUSPEND=true` and `SMOKE_ONLY=true`.
4. Create a one-off job from the CronJob and inspect logs/artifacts. Smoke must prove DbSchemaCLI can connect/select using both generated aliases without running transfers.
5. Only after smoke passes, run one-corp/small-batch data movement with the CronJob still suspended.

## Retained artifacts

Artifacts live under `/opt/app-root/data/runs/<run-id>` for the pod lifetime. The CronJob uses `emptyDir`, so artifacts are retained only while the pod exists and while failed/successful job history keeps the pod around.

Expected files include:

- `refresh_corp_feed_<pid>.txt` — retained rolling-lookback corp feed in refresh mode.
- `subset_refresh.sql` — generated DbSchema master script.
- `subset_refresh_chunks/` — generated chunk scripts.
- `logs/refresh-flow.log`, `logs/cloud-sql-proxy.log`, `logs/dbschema-smoke.log`.
- `dbschema-smoke.sql` — non-secret smoke script containing only aliases and trivial select statements.
- `mv-refresh-plan.preflight.sql` when MV refresh is enabled.
- `postflight-helper-counts.txt` and, on trigger issues, `postflight-disabled-triggers.txt`.
- On failed runs, `failure-helper-counts.txt` and `failure-disabled-triggers.txt` when the target DB is reachable during diagnostics.

Logs and docs must not print passwords or full credential-bearing URLs. `init.sql` contains direct OCP secrets, is written with `0600`, and lives under `~/.DbSchema/cli/` outside `${RUN_DIR}`; do not copy it into tickets, retained artifacts, or persistent storage. `dbschema-smoke.sql` is safe to retain because it contains no credentials, transfer statements, or generated chunk SQL.

## Recovery after partial failures

The subset generator owns advisory locking, trigger suppression, helper tables, BCOMPS purge, deletes, and reloads. A failure can leave durable target-side state. The wrapper emits diagnostics and retained-artifact locations on failure, but intentionally does **not** automatically re-enable triggers or truncate helper tables; recovery must be a deliberate operator action. Recommended recovery:

1. Identify the failed pod and run id from logs: `run_id=... artifacts=/opt/app-root/data/runs/<run-id>`.
2. Copy non-secret artifacts before the pod is deleted, especially the retained corp feed and generated SQL.
3. Verify whether DbSchema is still running. If a stuck session holds the advisory lock, terminate the backend only after confirming no legitimate run is active.
4. Re-enable table triggers if needed using the retained rendered support script from the failed run, for example `${RUN_DIR}/subset_refresh_chunks/support/subset_enable_triggers.sql`, through `psql` or DbSchemaCLI against the target DB. Do **not** run source templates from `data-tool/scripts/subset/` directly because they contain generator tokens such as `__DBSCHEMA_TARGET_SCHEMA__`. If retained generated support scripts are unavailable, render the source template first with the exact validated schema, for example: `sed "s/__DBSCHEMA_TARGET_SCHEMA__/${DBSCHEMA_TARGET_SCHEMA}/g" data-tool/scripts/subset/subset_enable_triggers.sql | psql ...`.
5. Truncate helper tables if needed, using the configured target schema:
   ```sql
   \set target_schema '<DBSCHEMA_TARGET_SCHEMA>'
   TRUNCATE :"target_schema".subset_address_stage;
   TRUNCATE :"target_schema".subset_excluded_corp_parties;
   TRUNCATE :"target_schema".subset_excluded_events;
   TRUNCATE :"target_schema".subset_excluded_corps;
   ```
6. If failure happened before or during DbSchema transfer, rerun with the retained `refresh_corp_feed_<pid>.txt` as `FLOW_CORP_FILE` and `FLOW_MODE=refresh` to replay the same corp set instead of relying on a new rolling lookback. Keep `FLOW_RESET_EXTRACT_POSTGRES=false` for replay/delta runs.
7. If failure happened during MV refresh only, do not rerun the transfer just for MVs. Run `data-tool/refresh_colin_extract_views.sh --mode refresh --schema <DBSCHEMA_TARGET_SCHEMA> --targets <profile>` once target table state is confirmed healthy.
8. Re-run smoke/preflight before resuming scheduled execution.

## Rolling lookback limitation

Scheduled v1 uses the data-tool CLI rolling lookback (`--lookback-hours`, default 5) scoped by `--mig-batch-id`. It is **not** durable high-watermark processing. Downtime longer than the lookback can miss changes unless an operator reruns with a wider lookback or a retained/curated corp feed. Durable watermark/run-ledger support is follow-up work.

## Target schema and reset limitation

Source alias and target schema are configurable for the generated subset transfer path: `DBSCHEMA_SOURCE_CONNECTION` is rendered into transfer `from <alias>` clauses, and `DBSCHEMA_TARGET_SCHEMA` is rendered into generated helper/transfer SQL and used for `PGSCHEMA`/MV refresh.

The direct generator/flow defaults remain only for local compatibility. OCP deployments must pass explicit values for source alias, target alias, and target schema.

`refresh_colin_extract_views.sh --mode refresh --schema <schema>` is schema-aware for MV refresh. The separate reset/reapply path remains `public`-only unless the view DDL is separately schema-qualified; do not use reset/reapply for a non-`public` target schema without a separate validation/fix.

## Side-effect policy

- `cars*`: disabled by default via `FLOW_INCLUDE_CARS=false`. Enabling it runs a global cars* truncate/reload, not a corp-local delta.
- BCOMPS purge: enabled by the generator and target-wide for excluded corps computed from target data after load.
- Shared address upsert: current generator behavior merges Oracle addresses into the shared target `address` table by `addr_id`; this is not purely corp-local.
- Materialized views: disabled by default. When enabled, `legacy` refreshes whole selected MVs, not only changed corps.

## Production gate checklist

Do not set `SUSPEND=false` outside an approved rollout until all are complete:

- Cloud SQL role can disable/enable required triggers, truncate/write helper tables, create helper boolean casts, purge BCOMPS, and refresh/analyze selected MVs.
- DbSchemaCLI 9.7.1 starts headlessly through the free CLI path and can connect/select using both generated aliases.
- Oracle connectivity is proven from OCP.
- Target DB has current `colin_corps_extract_postgres_ddl` helper tables.
- `SMOKE_ONLY=true` OCP job succeeds and proves DbSchema target `${DBSCHEMA_TARGET_CONNECTION}`, `learn schema ${DBSCHEMA_TARGET_SCHEMA}`, and source `${DBSCHEMA_SOURCE_CONNECTION}` connect/select checks before any transfer.
- Generated SQL inspection with non-default source alias/schema confirms transfer statements use the configured source alias and helper/transfer objects use the configured target schema, with no unexpected `from cprd` or `public.` references.
- One-corp refresh succeeds.
- Small-batch refresh succeeds with retained artifacts verified.
- Recovery drill re-enables triggers and cleans helper tables.
- MV runtime is acceptable if MV refresh is enabled.
- Side-effect policy (`cars*`, BCOMPS, shared address, MVs) is approved.

## Validation commands

```bash
bash -n jobs/colin-extract-delta/run.sh
make -C jobs/colin-extract-delta validate
make -C jobs/colin-extract-delta template-required-params
# If pytest and local data-tool test dependencies are already available:
python -m pytest data-tool/tests/unit/flows/test_refresh_extract_subset_flow.py
```

`make validate` runs shell syntax, optional shellcheck, OpenShift YAML parsing if PyYAML is installed, rollout parameter checks, standalone OCP/data-tool contract checks, and a syntax compile of the current data-tool CLI entrypoint. The contract check validates generator rendering with non-default aliases/schema without pytest, and validates flow parser compatibility with the run.sh flag set when the flow's Python dependencies are installed. Do not add shell mocks for DbSchemaCLI smoke behavior; the meaningful gate requires DbSchemaCLI 9.7.1, staged JDBC drivers, and real endpoints.
