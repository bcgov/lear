### Steps to Transfer COLIN(Oracle) Corps Data to PostgreSQL Extract Database 

## Full refresh (existing workflow)

1. Create empty postgres extract db
   `createdb -h localhost -p 5432 -U postgres -T template0 colin-mig-corps-data-test`

2. Create COLIN corps postgres extract table structure via ddl in `/data-tool/scripts/colin_corps_extract_postgres_ddl`

### create empty db for the first time
```bash
createdb -h localhost -p 5432 -U postgres -T template0 colin-mig-corps-data-test &&
psql -v ON_ERROR_STOP=1 -h localhost -p 5432 -U postgres -d colin-mig-corps-data-test -f <lear-repo-base-path>/data-tool/scripts/colin_corps_extract_postgres_ddl

kill connection & recreate empty db

psql -h localhost -p 5432 -U postgres -d colin-mig-corps-data-test -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE datname = 'colin-mig-corps-data-test' AND pid <> pg_backend_pid();" &&
dropdb -h localhost -p 5432 -U postgres colin-mig-corps-data-test &&
createdb -h localhost -p 5432 -U postgres -T template0 colin-mig-corps-data-test &&
psql -v ON_ERROR_STOP=1 -h localhost -p 5432 -U postgres -d colin-mig-corps-test -f <lear-repo-base-path>/data-tool/scripts/colin_corps_extract_postgres_ddl
```

The canonical DDL installs the address-transpose routines through
`\ir colin_address_transpose_updates.sql`. Run this DDL with `psql`; it installs
the routines but does not run the transpose.

3. Install DbSchemaCLI (previously named DbShell) - [DbSchemaCLI | Free Universal SQL Command-Line Client](https://dbschema.com/dbschemacli.html).
   More general info around configuration and data transfer can be found at: [DbSchemaCLI | Universal Command Line Client](https://dbschema.com/documentation/dbschemacli.html)

4. Add `/Applications/DbSchema` to path

5. Register Oracle driver and extract source db in `~/.DbSchema/cli/init.sql`
```bash
register driver Oracle oracle.jdbc.OracleDriver jdbc:oracle:thin:@<host>:<port>:<db> "port=1521"
connection cprd -d Oracle -u <some_user> -p <some_password> -h <host_name> -P <port> -D <database_name>
```

6. Register PostgreSQL driver and extract target db in `~/.DbSchema/cli/init.sql`
```bash
register driver PostgreSql org.postgresql.Driver jdbc:postgresql://<host>:<port>/<db> "port=5432"
connection cprd_pg -d PostgreSql -u postgres -p <some_password> -h localhost -P <port> -D colin-mig-corps-data-test
```

7. Transfer data (full refresh)
   `dbschemacli <lear-repo-base-path>/data-tool/scripts/transfer_cprd_corps.sql`

8. Successful output will look something like following:
```bash
argus@Argus-Mac ~/h3/git/bcreg/lear/data-tool/scripts $ dbschemacli /Users/argus/h3/git/bcreg/lear/data-tool/scripts/transfer_cprd_corps.sql
DbSchemaCLI #250319
Type 'help' for a list of commands.

Processing file /Users/argus/h3/git/bcreg/lear/data-tool/scripts/transfer_cprd_corps.sql
Connected

Transfer using 8 thread(s) corporation ...      2936 rows in 00:39. Reader waited 00:00, writer 03:21.
Transfer using 8 thread(s) event ...            22415 rows in 00:16. Reader waited 00:00, writer 01:13.
Transfer using 8 thread(s) corp_name ...        3171 rows in 00:16. Reader waited 00:00, writer 01:04.
Transfer using 8 thread(s) corp_state ...       2939 rows in 00:17. Reader waited 00:00, writer 01:20.
Transfer using 8 thread(s) filing ...           21680 rows in 00:24. Reader waited 00:00, writer 02:08.
Transfer using 8 thread(s) filing_user ...      20889 rows in 00:27. Reader waited 00:00, writer 02:17.
...
```

9. Re-index target extract db.

10. Use "count overview" SQL snippet in `misc_extract_corps_queries.sql` to verify the db changes.

Notes:
1. Update number of threads (e.g. `vset cli.settings.transfer_threads=4`) to use as appropriate in `transfer_cprd_corps.sql`.
2. After loading the data, `transfer_cprd_corps.sql` calls
   `public.colin_address_transpose(NULL)` while holding the advisory lock, then
   releases the lock. DbSchemaCLI displays one JSON value with eight phase counts, their total, and elapsed seconds.

---

## Running without superuser

The supported restricted path uses one owner identity for the extract database and all
objects in `public`. During a load, `drop_constraints` temporarily removes every
foreign key in `public`, so suppression applies to all DbSchemaCLI writer sessions.
The constraints are restored afterward as `NOT VALID`. The database must be quiesced
during the drop/load/restore window. Any user-defined triggers added outside this
repository are **not** disabled by this method and will continue to fire.

### One-time bootstrap vs. steady-state privileges

| Phase | PostgreSQL privileges / ownership | Oracle privileges |
|---|---|---|
| One-time DBA bootstrap | Superuser creates or adopts the login and database, transfers database and `public` schema ownership, and installs the `varchar -> boolean` and `bpchar -> boolean` casts. Repeat the cast install whenever the database is dropped/recreated. | None. |
| DDL installation | The restricted role owns the database and `public` schema and applies both DDL files itself, thereby owning all extract tables, sequences, views, materialized views, functions, and procedures. | None. |
| Steady-state load/refresh | `LOGIN` plus object ownership. The role does **not** need `SUPERUSER`, `CREATEDB`, or `CREATEROLE`, and no additional grantable PostgreSQL privileges are required. | Existing source login plus `SELECT` on every COLIN source object used by the full/subset queries. See the privilege audit in `docs/plans/nonsuperuser_refresh_plan.md`. |

Optional privileges are not part of the supported path: `pg_signal_backend` is needed
only to terminate other users' sessions, and PostgreSQL 15+
`GRANT SET ON PARAMETER session_replication_role` is relevant only to the legacy
`replica_role` method. Neither is needed with `drop_constraints`, and restricted
runs must not drop/recreate their database.

If policy separates login and ownership, a non-login owner role granted to the login
is equivalent, but both runtime connection mechanisms must receive the same membership
and must be tested for owner checks.

### Provision in this order

Use a PostgreSQL superuser from a maintenance database. The bootstrap file is
idempotent where PostgreSQL permits and deliberately does not contain a password;
configure authentication through the deployment's approved secret mechanism.

1. **Create/adopt the role and database, then transfer the database and schema:**

   ```bash
   psql -X -v ON_ERROR_STOP=1 -h <host> -p <port> -U <dba> -d postgres \
     -v role=colin_extract -v dbname=colin_extract \
     -f <lear-repo-base-path>/data-tool/scripts/bootstrap/colin_extract_restricted_bootstrap.sql
   ```

2. **Apply the base DDL and then the derived view/MV DDL as that restricted role:**

   ```bash
   psql -X -v ON_ERROR_STOP=1 -h <host> -p <port> -U colin_extract -d colin_extract \
     -f <lear-repo-base-path>/data-tool/scripts/colin_corps_extract_postgres_ddl
   psql -X -v ON_ERROR_STOP=1 -h <host> -p <port> -U colin_extract -d colin_extract \
     -f <lear-repo-base-path>/data-tool/scripts/colin_corps_extract_postgres_views_ddl
   ```

3. **Install the database-scoped casts once as a superuser:**

   ```bash
   psql -X -v ON_ERROR_STOP=1 -h <host> -p <port> -U <dba> -d colin_extract \
     -f <lear-repo-base-path>/data-tool/scripts/subset/subset_pg_boolean_casts.sql
   ```

   The installer is self-contained and technically may run any time after database
   creation. Running it after the role-owned DDL makes the ownership boundary explicit:
   the DBA owns the cast helper functions/casts, and restricted runs only verify them.
   A missing bootstrap fails before transfer at
   `subset_pg_boolean_casts_verify.sql`.

4. **Run the full or subset workflow with the restricted identity.** The full
   refresh needs no boolean casts because it temporarily converts the affected columns
   to integers. Register `cprd_pg` with the restricted role and run the existing
   `transfer_cprd_corps.sql`; it now uses the FK drop/restore procedures automatically.

   For a subset load/refresh, generate with both restricted modes:

   ```bash
   python <lear-repo-base-path>/data-tool/scripts/generate_cprd_subset_extract.py \
     --corp-file <corp-id-file> \
     --mode refresh \
     --pg-disable-method drop_constraints \
     --pg-cast-mode verify \
     --out <lear-repo-base-path>/data-tool/scripts/_generated/subset_refresh.sql
   ```

   For the flow entry point, pass the same privilege modes and explicitly disable its
   database reset:

   ```bash
   python <lear-repo-base-path>/data-tool/flows/refresh_extract_subset_flow.py \
     --mode refresh \
     --pg-disable-method drop_constraints \
     --pg-cast-mode verify \
     --reset-extract-postgres
   ```

   **Flag inversion warning:** `--reset-extract-postgres` is implemented with
   `action='store_false'`; passing it disables reset, while omitting it enables the
   destructive drop/create path. Restricted runs must pass it. The
   `--run-dbschemacli` and `--refresh-views` flags have the same inverted behavior:
   passing either flag disables that action, so omit them when the flow should execute
   DbSchemaCLI and refresh views.

### Runtime identity requirement

The flow's psql/SQLAlchemy connections use the `DATABASE_*_COLIN_MIGR`
credentials, while DbSchemaCLI uses the registered target connection
(`cprd_pg`, `cprd_pg_subset`, or `--target-connection`). Both must authenticate
as the same restricted owner identity; otherwise one half of the run can fail owner
checks even if the other succeeds. Confirm the DbSchemaCLI registration and environment
together before the first run. A direct generator diagnostic run may add
`--pg-debug-session-probes` to print `current_user` for the generated master/nested
sessions; the ownership model still requires the separately opened transfer writers
to use the same identity.

### Existing extract databases

Before the edited full-refresh script or a subset run using `drop_constraints`, an
existing database created from older DDL needs the FK module installed once by its
object-owning restricted role:

```bash
psql -X -v ON_ERROR_STOP=1 -h <host> -p <port> -U colin_extract -d <existing-db> \
  -f <lear-repo-base-path>/data-tool/scripts/colin_fk_constraint_updates.sql
```

Also install the boolean casts as the DBA if they are absent, then use
`--pg-cast-mode verify`. If the existing extract objects are still owned by
`postgres`, grants alone are insufficient: have the DBA transfer the complete
extract object set to the restricted owner or, preferably, provision a fresh database
with the ordered procedure above. Do not reapply the full base DDL over a populated
database merely to obtain the FK module.

Dropping/recreating a restricted database is a DBA re-provisioning event: rerun the
bootstrap, reapply both DDLs as the restricted owner, and reinstall the casts as the
DBA. For load mode, target a pre-provisioned empty database and keep the flow reset
disabled.

### `NOT VALID`, trigger, and recovery caveats

Restored foreign keys enforce all new writes but do not scan existing rows.
`pg_constraint.convalidated` remains false, and `psql \d` reports `NOT VALID`.
This is intentional because the extract can contain known legacy exceptions, including
amalgamating-corporation references outside the extracted cohort. Do not run blanket
`VALIDATE CONSTRAINT`; validate only a specifically understood constraint when its
data is known to be clean.

The FK procedures must be invoked as top-level autocommit `CALL` statements, not
inside an explicit transaction. If a run fails in the suppression window:

1. Stop other writers and reconnect as the same restricted owner. A disconnected
   DbSchemaCLI session releases its session advisory lock.
2. Restore every captured constraint (safe to repeat; a second call is a no-op):

   ```sql
   CALL public.colin_fk_restore_all(NULL);
   ```

3. For an interrupted full refresh, re-run the reverse
   `ALTER COLUMN ... TYPE boolean USING ...::boolean` statements if any indicator
   columns were left as integers.
4. Confirm `public.colin_dropped_fks` is empty, repair any reported restore error, and
   rerun the extract. A failed restore retains its helper row, so the same `CALL` can
   resume without catalog surgery.

### Performance validation status

The manual comparison of the standard Oracle corp list under superuser
`table_triggers` versus restricted `drop_constraints` is **deferred** because it
requires Oracle and DbSchemaCLI access. No timing result is claimed here. When those
external dependencies are available, record both runs with the same corp list,
PostgreSQL target class, DbSchemaCLI version/thread count, and fast-load settings.

---

## Preserved-table backup, full restore, and delta restore

The preserved migration/tracking/auth side-table list is centralized in `data-tool/scripts/restore/preserved_tables.conf` and is shared by:

- `data-tool/backup_extract_tables.sh` — creates a preserved-table dump and `<dump>.manifest.json` sidecar.
- `data-tool/restore_extract.sh` — full preserved-table restore after an extract rebuild.
- `data-tool/delta_restore_extract.sh` — preview/validate/apply merge for preserved tables.

Start with the [preserved-table overview](restore/README_add_preserved_table_overview.md). To add a table, use the [quick reference](restore/README_add_preserved_table_quickref.md) or [full guide](restore/README_add_preserved_table.md).

For the delta workflow, see [restore/README_delta_restore.md](restore/README_delta_restore.md). It provides the golden path, a complete CLI/environment reference, and troubleshooting by exit code.

`DELTA_MODE=true ./restore_extract.sh` has been removed by design. The full restore script now aborts with a pointer to `data-tool/delta_restore_extract.sh`; run explicit delta preview, validate, and apply commands instead.

Delta restore uses the same PostgreSQL advisory-lock SQL as the subset/full-refresh scripts. Avoid running migration flows or other non-cooperating writers against the target database during apply.

---

## Resetting the derived COLIN view/materialized-view layer

Use this when the **derived view/MV definitions** in `colin_corps_extract_postgres_views_ddl` have changed and you need to drop + recreate just that layer in an existing extract DB.

Files:
- Drop-plan generator: `data-tool/scripts/colin_corps_extract_generate_view_drop.sql`
- Wrapper: `data-tool/reset_colin_extract_views.sh`
- Reapply DDL: `data-tool/scripts/colin_corps_extract_postgres_views_ddl`

Usage summary:
```text
./data-tool/reset_colin_extract_views.sh [options]

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

Environment defaults:
  PGDATABASE=colin-mig-corps-test
  PGUSER=postgres
  PGHOST=localhost
  PGPORT=5432
  PGSCHEMA=public
```

Examples:
```bash
# Safe preview: print the generated dependency-aware drop plan only
./data-tool/reset_colin_extract_views.sh \
  --mode plan \
  --db colin-mig-corps-test-subset \
  --user postgres

# Drop the allowlisted derived objects, then recreate them from the views DDL
./data-tool/reset_colin_extract_views.sh \
  --mode reset --yes \
  --db colin-mig-corps-test-subset \
  --user postgres

# If the derived objects are already absent and you only want to recreate them,
# add --allow-empty explicitly.
./data-tool/reset_colin_extract_views.sh \
  --mode reset --yes --allow-empty \
  --db colin-mig-corps-test-subset \
  --user postgres
```

Safety rules:
- Only the COLIN-owned allowlisted views/materialized views are targeted.
- The generator **does not use `CASCADE`**.
- The generator **fails** if an unexpected non-allowlisted view/materialized view depends on a COLIN-owned object.
- `reset` mode currently supports only schema `public` because `colin_corps_extract_postgres_views_ddl` is not schema-qualified.
- Base tables must already exist before resetting/recreating the derived view layer.
- For DDL or MV-column definition changes, including materialized-view definition changes, run `reset_colin_extract_views.sh --mode reset --yes` or the equivalent derived-layer reset path before running code that references the changed MV layer.
- For **data-only** changes, prefer `REFRESH MATERIALIZED VIEW` rather than drop/recreate.

---

## Dumping the extract DB without derived views/materialized views

Creates a tar-format `pg_dump` archive excluding the COLIN derived views/materialized views.

```bash
PGPASSFILE=~/.pgpass \
  DUMP=/tmp/colin-no-views-test.tar \
  ./data-tool/dump_colin_extract_without_views.sh
```

Options:
- `MODE`: `dump` (default) runs `pg_dump`; `print` only prints the command.
- `PG_DUMP_BIN`: `pg_dump` binary to use (default: `pg_dump`).
- `PGHOST`: database host (default: `localhost`).
- `PGPORT`: database port (default: `5432`).
- `PGUSER`: database user (default: `postgres`).
- `PGDATABASE`: source database (default: `colin-mig-corps-test`).
- `PGSCHEMA`: schema for excluded views/materialized views (default: `public`).
- `PGPASSFILE`: password file for libpq authentication, e.g. `~/.pgpass`.
- `PGPASSWORD`: one-off password alternative to `PGPASSFILE`.
- `BACKUP_DIR`: output directory when `DUMP` is not set (default: current directory).
- `DUMP`: full output path and filename; overrides `BACKUP_DIR`.

After restore, recreate the derived layer with `reset_colin_extract_views.sh --mode reset --yes --allow-empty ...` if needed.

Quick check; no output means no view/materialized-view entries were found in the archive list:

```bash
pg_restore -l /tmp/colin-no-views-test.tar | grep -E 'VIEW|MATERIALIZED VIEW'
```

---

## Refreshing selected materialized views for data-only changes

Use this when the **derived MV definitions have not changed** and you only need to rebuild the affected materialized views in dependency order. If a materialized-view definition changes, use the reset/recreate workflow instead of refresh-only.

Files:
- Wrapper: `data-tool/refresh_colin_extract_views.sh`
- MV DDL reference: `data-tool/scripts/colin_corps_extract_postgres_views_ddl`

Usage summary:
```text
./data-tool/refresh_colin_extract_views.sh [options]

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
```

Refresh profiles:
- `legacy`: refresh `mv_admin_email_count`, then `mv_corp_event_filing_rollup`, then `mv_admin_email_bad_email_flags`, then `mv_legacy_corps_data` (safe/default legacy-screening refresh; keeps normalized email-used counts, rolling time-windowed counts, and bad-email flags current)
- `legacy-direct`: refresh `mv_legacy_corps_data` only (advanced/leaf-only path when all upstream sidecars/derived MVs are already current and analyzed)
- `event-filing`: alias of `legacy`; refresh `mv_admin_email_count`, then `mv_corp_event_filing_rollup`, then `mv_admin_email_bad_email_flags`, then `mv_legacy_corps_data`
- `share`: refresh `mv_admin_email_count`, then `mv_share_class_issue_flags`, the event/filing rollup, `mv_admin_email_bad_email_flags`, then `mv_legacy_corps_data`
- `address`: refresh `mv_admin_email_count`, then `mv_addr_issue_counts_by_entity`, the legacy-only address screening chain (`mv_addr_quality_screening_by_corp`), the event/filing rollup, `mv_admin_email_bad_email_flags`, then `mv_legacy_corps_data`
- `address-full`: refresh `mv_admin_email_count`, then `mv_addr_issue_counts_by_entity`, both address-quality layers, the event/filing rollup, `mv_admin_email_bad_email_flags`, legacy MV, and corp issue reporting MVs
- `party`: refresh the legacy-only `corp_party` screening chain, then normalized email count and address screening chain: `mv_corps_with_officers`, `mv_corps_party_role_count`, `mv_admin_email_count`, `mv_addr_issue_counts_by_entity`, `mv_addr_quality_screening_by_corp`, the event/filing rollup, `mv_admin_email_bad_email_flags`, then `mv_legacy_corps_data`
- `party-full`: refresh the `corp_party` chain, `mv_admin_email_count`, `mv_addr_issue_counts_by_entity`, both address-quality layers, event/filing rollup, `mv_admin_email_bad_email_flags`, legacy MV, and corp issue reporting MVs
- `admin-email`: refresh `mv_admin_email_count`, plus the event/filing rollup, then `mv_admin_email_bad_email_flags`, then `mv_legacy_corps_data`
- `email-domain`: refresh `mv_admin_email_domain_count` only
- `corp-issues`: refresh `mv_addr_issue_counts_by_entity`, `mv_addr_quality_by_corp`, `mv_corp_issue_flags`, then `mv_issue_counts_by_corp_type`
- `all`: refresh the full COLIN MV layer in dependency order, including `mv_addr_issue_counts_by_entity`

Examples:
```bash
# Safe preview: refresh the full legacy-screening chain
./data-tool/refresh_colin_extract_views.sh \
  --targets legacy \
  --db colin-mig-corps-test-subset \
  --user postgres

# Rebuild event/filing-derived data first, then mv_legacy_corps_data
./data-tool/refresh_colin_extract_views.sh \
  --mode refresh \
  --targets event-filing \
  --db colin-mig-corps-test-subset \
  --user postgres

# Refresh address-driven legacy screening data and issue reporting together
./data-tool/refresh_colin_extract_views.sh \
  --mode refresh \
  --targets address-full \
  --db colin-mig-corps-test-subset \
  --user postgres
```

Notes:
- Use `reset_colin_extract_views.sh` when the view/MV DDL itself has changed; refresh-only does not apply changed definitions.
- `mv_legacy_corps_data.email_used_count` is based on normalized `lower(btrim(admin_email))` values from `mv_admin_email_count`, so case/space variants count as the same admin email.
- BAR data is static and should no longer be treated as a reason to refresh `mv_legacy_corps_data`.
- `legacy` is the safe/default profile for legacy-screening data, including refreshes after normalized admin-email count changes, email exclusion table edits, or `bad_emails` row edits.
- `legacy-direct` is an advanced/leaf-only path that assumes all upstream sidecars/derived MVs, including `mv_admin_email_count` and `mv_admin_email_bad_email_flags`, are already current and analyzed; otherwise `mv_legacy_corps_data` can be refreshed against stale inputs, stale email-used counts, and stale bad-email flags.
- `event-filing` is kept as an explicit alias of `legacy` for event/filing-driven refreshes.
- Address-driven profiles now refresh `mv_addr_issue_counts_by_entity` first so the slim and full address-quality MVs share the same upstream aggregation.
- `address` / `party` stop at the slim screening MV for legacy-only refreshes.
- `address-full` / `party-full` / `corp-issues` continue through `mv_addr_quality_by_corp` for full-wide address issue reporting.
- The refresh helper assumes the materialized views already exist and now preflights the selected targets before generating/executing the plan.
- Roll out normalized email-count definition changes by applying/recreating the derived MV definitions, refreshing/analyzing `mv_admin_email_count` before `mv_legacy_corps_data`, validating count and SAF eligibility deltas, and capturing a new refresh timing baseline.

---

## Subset refresh / subset load (corp-id list; 10k+ supported)

This workflow is for when you want to:
- **refresh**: delete + reload a specific list of businesses in an existing Postgres extract DB, or
- **load**: load only a specific list of businesses (useful for empty/sandbox extract DBs).

Key constraints handled:
- No Oracle temp tables required.
- Oracle IN-list limit (~1000 items) is handled via `--oracle-in-strategy` (default `auto`) using `--chunk-size` (default 900).
- Subset scripts do **not** run boolean↔integer ALTER COLUMN TYPE flips (important when the extract DB is already populated).

### Files involved

Core templates (always used in subset workflow):
- `data-tool/scripts/subset/subset_disable_triggers.sql`
- `data-tool/scripts/subset/subset_enable_triggers.sql`
- `data-tool/scripts/subset/subset_delete_chunk.sql`
- `data-tool/scripts/subset/subset_transfer_chunk.sql`
- `data-tool/scripts/subset/subset_pg_acquire_advisory_lock.sql` / `subset_pg_release_advisory_lock.sql` (serialize subset runs per target DB)
- `data-tool/scripts/subset/subset_pg_cleanup_orphan_children.sql` (refresh-only orphan child cleanup before chunked deletes)
- `data-tool/scripts/subset/subset_pg_boolean_casts.sql` (required so DbSchemaCLI can insert 't'/'f' into boolean columns)
- `data-tool/scripts/subset/subset_pg_purge_bcomps_excluded.sql` (run once after transfer)
- `data-tool/scripts/subset/subset_pg_call_address_transpose.sql` (runs address transpose once)

Optional Postgres session performance templates (only when `--pg-fastload` is used):
- `data-tool/scripts/subset/subset_pg_fastload_begin.sql`
- `data-tool/scripts/subset/subset_pg_fastload_end.sql`

cars* global refresh templates (only when cars are included; skipped with `--no-cars`):
- `data-tool/scripts/subset/subset_delete_cars.sql`
- `data-tool/scripts/subset/subset_transfer_cars.sql`

Generator:
- `data-tool/scripts/generate_cprd_subset_extract.py`

Generated scripts (gitignored by default):
- **Main script**: runs templates + the per-chunk scripts, e.g. `data-tool/scripts/_generated/subset_refresh.sql`
- **Chunk scripts**: generated per chunk in `data-tool/scripts/_generated/chunks/`
  - `subset_delete_chunk_0001.sql`, `subset_transfer_chunk_0001.sql`, etc.

### Steps

1. Put your corp list into a text file, 1 per line (comments allowed using `#`).
   Example: `data-tool/scripts/corp_ids.txt`

2. Generate the subset scripts:

   **Refresh mode** (delete then reload those corps):
   ```bash
   python <lear-repo-base-path>/data-tool/scripts/generate_cprd_subset_extract.py \
     --corp-file <lear-repo-base-path>/data-tool/scripts/corp_ids.txt \
     --mode refresh \
     --chunk-size 500 \
     --threads 4 \
     --pg-fastload \ 
     --pg-disable-method table_triggers \   
     --out <lear-repo-base-path>/data-tool/scripts/_generated/subset_refresh.sql
   ```

   **Refresh mode with CP corps included**:
   ```bash
   python <lear-repo-base-path>/data-tool/scripts/generate_cprd_subset_extract.py \
     --corp-file <lear-repo-base-path>/data-tool/scripts/corp_ids.txt \
     --mode refresh \
     --chunk-size 500 \
     --threads 4 \
     --include-cp \
     --pg-fastload \ 
     --pg-disable-method table_triggers \   
     --out <lear-repo-base-path>/data-tool/scripts/_generated/subset_refresh.sql
   ```

   **Load mode** (load only those corps; no deletes):
   ```bash
   python <lear-repo-base-path>/data-tool/scripts/generate_cprd_subset_extract.py \
     --corp-file <lear-repo-base-path>/data-tool/scripts/corp_ids.txt \
     --mode load \
     --chunk-size 500 \
     --threads 4 \
     --pg-fastload \ 
     --pg-disable-method table_triggers \      
     --out <lear-repo-base-path>/data-tool/scripts/_generated/subset_load.sql
   ```

   Optional flags:
   - Add `--include-cp` to opt in corp type `CP` for the subset transfer queries.
   - `--include-cp` affects the **subset workflow only**. Full refresh (`transfer_cprd_corps.sql`) and downstream reservation flows still use the historical corp-type cohort unless updated separately.
   Optional performance flags:
   - Add `--pg-fastload` to enable Postgres session settings for faster bulk writes (templates `subset_pg_fastload_begin.sql` / `subset_pg_fastload_end.sql`).
   - `--pg-disable-method` accepts `table_triggers`, `replica_role`, and `drop_constraints`; use `drop_constraints` for the restricted-owner path, which restores foreign keys as `NOT VALID`.
   - The actual generator default is `table_triggers`, not `replica_role`.
   - In refresh mode, preserved rows in `corp_processing`, `auth_processing`, `affiliation_processing`, and `colin_tracking` still reference `corporation` / `event`, so FK enforcement must stay suppressed across delete/reload. The generator now adds refresh-only trigger suppression for those preserved FK-owning tables when `--pg-disable-method table_triggers` is used.
   - Subset load/refresh scripts acquire a session-level Postgres advisory lock at the start and release it at the end. The same lock key is used by the full refresh script.
   - `table_triggers` changes table trigger state globally while the refresh runs, so use it against a quiesced/disposable extract DB and with a role that can disable the relevant triggers.
   - If you use `replica_role`, remember it is session-local. If FK errors still occur, verify `current_setting('session_replication_role')` inside the nested delete/purge scripts being executed by DbSchemaCLI.
   - `address` is treated as a shared/global table during subset refresh/load. The generator now reuses the predeclared helper staging table `public.subset_address_stage`, transfers incoming Oracle addresses into it, and merges them into `public.address` by `addr_id` instead of deleting/reinserting address rows directly. The address extract also includes `notification_resend` references.
   - BCOMPS purge keysets also use predeclared helper tables in the extract schema: `public.subset_excluded_corps`, `public.subset_excluded_events`, and `public.subset_excluded_corp_parties`.
   - Do not overlap subset runs against the same target DB, and ensure the runtime role can truncate/read/write those helper tables.
   - Existing extract DBs created from older DDL must be refreshed or updated with the latest `colin_corps_extract_postgres_ddl` before running the subset workflow, otherwise the first helper-table `TRUNCATE` will fail.
   - Refresh mode now pre-cleans orphan event/corp-party child rows that can survive the parent-keyed delete phase from earlier failed/interleaved runs (for example a stale `filing` row whose parent `event` row is missing in target).
   - For diagnostics, add `--pg-debug-session-probes` (inline mode only). The generated SQL will print `pg_backend_pid()`, `current_user`, and `current_setting('session_replication_role')` in the master script and nested execute files so you can verify the master/nested `execute` session context during refresh. This does not directly instrument any separate DbSchemaCLI transfer writer sessions.

3. Run the generated main script with DbSchemaCLI:

   ```bash
   dbschemacli <lear-repo-base-path>/data-tool/scripts/_generated/subset_refresh.sql
   ```
   OR
   ```bash
   dbschemacli <lear-repo-base-path>/data-tool/scripts/_generated/subset_load.sql
   ```

    
### Notes / gotchas

- Chunk size is configurable. Keep `--chunk-size` <= 1000 to avoid Oracle IN-list failures.
- For small/medium subsets, consider `--oracle-in-strategy or_of_in_lists` (or leave it as the default `auto`) to avoid repeating the full transfer suite per chunk. See **Oracle IN-list strategy** below for details.
- Subset scripts automatically install a Postgres helper cast to allow DbSchemaCLI inserts of `t/f` into boolean columns.
- DbSchemaCLI build issue: If you get errors about `"bsh: for: No collection"` ensure you are using DbSchemaCLI 9.4.3+.
- If `--no-cars` is used, cars* tables are skipped entirely.
- Chunk templates are rendered at generation time (inline mode), so the resulting SQL is self-contained.
- If you need legacy runtime substitution behavior, generate with `--render-mode vset` (uses DbSchemaCLI `vset` + &placeholders).
- The generated master calls address transpose once after all chunks are loaded
  and before releasing the advisory lock. The returned JSON includes each phase count,
  their total, and elapsed seconds.

### Oracle IN-list strategy (`--oracle-in-strategy`)

Oracle has a practical limit of ~1000 items per `IN (...)` list. The subset generator supports two ways to stay under that limit, which are easy to conflate:

1. **Transfer execution chunking**: how many times we run the full transfer suite (all table transfers).
2. **IN-list grouping**: how many `IN (...)` groups are OR'd together inside a single transfer query.

Both are driven by `--chunk-size`, but you only get execution chunking when `--oracle-in-strategy` is `chunk_files` (or `auto` decides to fall back to it).

#### Decision logic

- `--oracle-in-strategy chunk_files`
  Always uses **transfer execution chunking**. The generator repeats the full transfer suite once per chunk: `ceil(N / chunk_size)` passes.

- `--oracle-in-strategy or_of_in_lists`
  Uses **IN-list grouping** inside the Oracle predicate so the transfer suite runs **once**, while still respecting the per-`IN` limit. The predicate looks like:
  `(corp_num IN (...<=chunk_size...)) OR (corp_num IN (...<=chunk_size...)) OR ...`
  In **refresh** mode, deletes are still executed in chunks, but the expensive transfer suite is a single pass.

- `--oracle-in-strategy auto` (default)
  Uses `or_of_in_lists` only when `N <= --or-of-in-max-ids` (default **10,000**). If the corp list is larger than that threshold, it falls back to `chunk_files`.

#### Strategy matrix

| Strategy | When used | Transfer suite runs | Oracle predicate shape |
|---|---|---:|---|
| `chunk_files` | Forced, or chosen by `auto` for very large lists | `ceil(N / chunk_size)` | `corp_num IN (...)` (single list per chunk file) |
| `or_of_in_lists` | Forced, or chosen by `auto` for small/medium lists | `1` | `(corp_num IN (...)) OR (corp_num IN (...)) ...` (many groups) |
| `auto` | Default | `1` or `ceil(N / chunk_size)` | Depends on threshold |

#### Concrete examples

- **Auto strategy, 30,000 corp ids (the common misunderstanding)**
  With defaults `--oracle-in-strategy auto --or-of-in-max-ids 10000 --chunk-size 1000`:
  - Because `30,000 > 10,000`, `auto` selects **`chunk_files`**.
  - You will get **30 chunk passes** (and ~30 transfer-suite executions) — *not* 3.
  - To reduce passes under `auto`, raise the threshold: `--or-of-in-max-ids 50000`.

- **Forced OR-of-IN-lists, 30,000 corp ids**
  If you explicitly set `--oracle-in-strategy or_of_in_lists --chunk-size 1000`:
  - The transfer suite runs **once**.
  - The Oracle predicate contains **30 IN groups OR'd together**.
  - In refresh mode, deletes still run in 30 chunks.

- **Small list, defaults**
  For `N=2,500` with defaults (`auto`, `chunk-size 900`):
  - `N <= 10,000` so `auto` uses **`or_of_in_lists`**.
  - Transfer suite runs once with `ceil(2500/900)=3` OR'd IN groups.

### Performance tuning

- Increase `--threads` for DbSchemaCLI transfer if your workstation and DB can handle it.
- Consider enabling `--pg-fastload` (see above) for faster bulk writes.
- If you have very large corp lists and performance is poor, consider switching `--oracle-in-strategy`:
  - `or_of_in_lists` is typically best for small/medium lists (single transfer pass).
  - `chunk_files` may be necessary for very large lists (because `auto` will fall back once the list exceeds `--or-of-in-max-ids`).
