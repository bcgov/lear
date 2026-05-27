# OpenShift deployment notes: COLIN extract delta

This package follows the external-CI image consumption pattern used by the newer SFTP job templates: `bc.yaml` creates only an ImageStream, while CI builds the repo-root Dockerfile and pushes `${NAME}:${IMAGE_TAG}`.

## Apply ImageStream

```bash
oc process -f jobs/colin-extract-delta/openshift/templates/bc.yaml \
  -p NAME=colin-extract-delta | oc apply -f -
```

## Deploy suspended CronJob

Keep schedules suspended by default. The CronJob template intentionally has no concrete defaults for rollout-specific values, so pass them explicitly:

```bash
oc process -f jobs/colin-extract-delta/openshift/templates/cronjob.yaml \
  -p NAME=colin-extract-delta \
  -p TAG=<environment-tag> \
  -p IMAGE_NAMESPACE=<tools-namespace> \
  -p IMAGE_TAG=<image-tag> \
  -p DBSCHEMA_SOURCE_CONNECTION=<source-oracle-alias> \
  -p DBSCHEMA_TARGET_CONNECTION=<target-postgres-alias> \
  -p DBSCHEMA_TARGET_SCHEMA=<target-postgres-schema> \
  -p GCP_SA_SECRET_NAME=<gcp-service-account-secret> \
  -p GCP_SA_SECRET_KEY=<gcp-service-account-json-key> \
  -p SUSPEND=true \
  -p SMOKE_ONLY=true | oc apply -f -
```

Create the main job secret separately. Minimum keys are documented in `../README.md`. For JSON-key Cloud SQL proxy mode, create `${GCP_SA_SECRET_NAME}` with key `${GCP_SA_SECRET_KEY}`; Workload Identity/ambient ADC deployments may use an explicitly supplied unused optional secret only after validation.

## Smoke-only run

```bash
oc create job --from=cronjob/colin-extract-delta-<environment-tag> colin-extract-delta-<environment-tag>-smoke-$(date +%s)
oc logs -l job-name=<created-job-name> --tail=-1
```

A smoke run starts or validates the Cloud SQL proxy endpoint, checks Postgres helper tables in `${DBSCHEMA_TARGET_SCHEMA}`, checks Oracle connectivity, verifies DbSchemaCLI startup, validates the generated target `${DBSCHEMA_TARGET_CONNECTION}`, `learn schema ${DBSCHEMA_TARGET_SCHEMA}`, and source `${DBSCHEMA_SOURCE_CONNECTION}` with non-mutating connect/select checks, and optionally validates MV targets. It exits before generator/DbSchema transfer and does not move data.

## Cloud SQL proxy modes

- `wrapper` (default): `run.sh` starts `cloud-sql-proxy`, waits for localhost TCP, and cleans it up with a trap. Use this unless native sidecar support is confirmed for the target OCP/Kubernetes version.
- `external` / `sidecar`: another container/process provides `127.0.0.1:${CLOUDSQL_PROXY_PORT}`. Be careful with regular sidecars in Jobs because they can keep pods running after the main container exits.
- `disabled`: use only for direct Postgres networking where the target host/port are injected separately.

JSON-key mode mounts `${GCP_SA_SECRET_NAME}` key `${GCP_SA_SECRET_KEY}` at `/var/secrets/google/cloudsql-service-account.json`. Workload Identity or ambient ADC may rely on the optional volume being absent only if validated; still pass explicit template parameter values so rollout inputs are deliberate.

## Rollout sequence

1. Apply ImageStream and push image.
2. Apply CronJob with `SUSPEND=true`, `SMOKE_ONLY=true`.
3. Run one-off smoke job.
4. Before enabling data movement, inspect generated SQL from a non-default source alias/schema run and confirm transfer statements use `from <DBSCHEMA_SOURCE_CONNECTION>` and helper/transfer objects use `<DBSCHEMA_TARGET_SCHEMA>.`, with no unexpected `from cprd` or `public.` references.
5. Switch `SMOKE_ONLY=false`, keep `SUSPEND=true`, run one-corp refresh using a curated `FLOW_CORP_FILE` if needed (`FLOW_MODE=refresh`, `FLOW_RESET_EXTRACT_POSTGRES=false`).
6. Run small-batch refresh with default `FLOW_INCLUDE_CARS=false` and `REFRESH_COLIN_EXTRACT_VIEWS=false`.
7. If approved, test `REFRESH_COLIN_EXTRACT_VIEWS=true` with `MV_REFRESH_TARGETS=legacy` and the configured `DBSCHEMA_TARGET_SCHEMA`.
8. Record runtime/memory/CPU/lock duration and tune resources/deadline.
9. Complete production checklist in `../README.md` before setting `SUSPEND=false`.

## Operational reminders

- Artifacts are in the pod `emptyDir` under `/opt/app-root/data/runs/<run-id>` and disappear when the pod is deleted.
- Failed/successful job history limits determine how long pods remain discoverable.
- The rolling lookback is not a durable watermark; use retained corp feeds for exact reruns after partial failures.
- Keep `FLOW_INCLUDE_CARS=false` unless the global cars* side effect is explicitly approved.
- OCP must supply explicit source alias, target alias, and target schema values; local data-tool defaults are compatibility defaults only.
- The MV refresh path accepts a schema, but reset/reapply remains `public`-only unless the views DDL is separately schema-qualified. Do not use reset/reapply for a non-`public` target schema without a separate fix/validation.
