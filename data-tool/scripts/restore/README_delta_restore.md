# Delta restore for preserved COLIN extract tables

`data-tool/delta_restore_extract.sh` merges a preserved-table dump into an existing COLIN PostgreSQL extract database without truncating the preserved tables. It is the replacement for the old `DELTA_MODE=true` prototype in `restore_extract.sh`.

Use it when a developer/local extract database already has migration/tracking/auth side-table data that should be reconciled with a newer preserved-table dump.

## What it operates on

The preserved table set and phase order are centralized in:

```text
data-tool/scripts/restore/preserved_tables.conf
```

The same file is consumed by:

- `data-tool/backup_extract_tables.sh` — creates the preserved-table dump and sidecar manifest.
- `data-tool/restore_extract.sh` — full restore path.
- `data-tool/delta_restore_extract.sh` — delta preview/apply path.

## Connection defaults

The script uses libpq environment variables:

```bash
PGHOST=localhost
PGPORT=5432
PGUSER=postgres
PGDATABASE=colin-mig-corps-test
PGPASSWORD=...        # optional; or use .pgpass
```

## Basic usage

Create a preserved-table dump from the source extract database:

```bash
cd data-tool
PGDATABASE=source_extract \
BACKUP_DIR=/tmp/preserved \
./backup_extract_tables.sh
```

Preview a merge into the target database:

```bash
cd data-tool
PGDATABASE=local_extract \
./delta_restore_extract.sh \
  --dump /tmp/preserved/keep_YYYY-MM-DD.dump \
  --mode preview
```

Apply selected rows after reviewing the preview:

```bash
cd data-tool
PGDATABASE=local_extract \
./delta_restore_extract.sh \
  --dump /tmp/preserved/keep_YYYY-MM-DD.dump \
  --mode apply \
  --selection-file scripts/generated/delta_restore/<run>/selection.conf \
  --yes
```

Clean up leftover delta schemas from an interrupted run:

```bash
cd data-tool
PGDATABASE=local_extract ./delta_restore_extract.sh --cleanup
```

## Modes and artifacts

### Preview mode

Preview is the default. It:

1. Verifies the dump and optional `<dump>.manifest.json` sha256.
2. Filters the dump TOC to the preserved table list.
3. Creates run-scoped schemas: `delta_stage`, `delta_map`, `delta_diff`, `delta_ctl`.
4. Streams data into `delta_stage` with guarded COPY-target rewriting.
5. Runs schema-drift preflight.
6. Classifies staged rows and builds ID maps. Preview classification and preview-report SQL run inside the delta session wrapper (`20_session_begin.sql` / `21_session_end.sql`), so they use the same high-work-memory settings as staging/apply.
7. Writes:
   - `preview.txt`
   - `selection.conf`
   - `classification.out` / `classification.err` with classification stdout and timing notices
   - `temp_stats.tsv` with before/after `pg_stat_database` temp file/byte counters around classification
   - `preview_lines.out` / `preview_lines.err` for preview report rendering
   - count TSVs and diagnostic SQL/stdout/stderr files

Artifacts are written under:

```text
data-tool/scripts/generated/delta_restore/<UTC timestamp>/
```

### Apply mode

Apply mode re-runs staging/classification fresh, stamps the requested selection, validates dependencies, and applies selected rows in one `REPEATABLE READ` transaction. It then repairs sequences, analyzes touched tables, writes `apply_summary.txt`, and drops the delta schemas unless `--keep-artifacts` is supplied.

Apply requires `--yes` or an interactive `yes` confirmation.

## Class semantics

| Class | Meaning | Applyable? |
| --- | --- | --- |
| `NEW` | Staged row has no safe local match. For ID tables, the map records whether the dump ID can be preserved or must be reallocated. | Yes, by default |
| `CHANGED` | Staged row matched a local row by natural key/hash but payload differs. Dump wins on apply. | Yes, by default |
| `CHANGED_LOCAL_NEWER` | Staged row matched local row but local `last_modified` is newer. | Only when explicitly included |
| `UNCHANGED` | Staged and local row are equivalent for compared columns. | No |
| `LOCAL_ONLY` | Local row has no staged match. Reported as a count only. | No |
| `BLOCKED_FK` | Required external or preserved-parent FK cannot be safely resolved. | No |
| `BLOCKED_PARENT` | Child row depends on a preserved parent that is blocked or ambiguous. | No |
| `AMBIGUOUS_NK` | Natural key is duplicated on staged and/or local side for an unenforced-NK table. | No |
| `SKIPPED_ABSENT` | Table is configured but absent from the dump. | No |

Natural-key matching is hash-accelerated where possible, but still keeps the null-safe natural-key residual check. This preserves existing behavior, including matches where natural-key components are `NULL`, while allowing PostgreSQL to use hashable equality for large staged/local comparisons.

`auth_component_operation` is append-only: novel hash-parent rows can be inserted; changed updates are not applied. Its `LOCAL_ONLY` count is scoped to local component rows under staged `auth_processing` parents that mapped to existing local parents; unrelated local auth-processing parents are not included in that diagnostic count.

During classification the database emits grep-friendly timing notices such as:

```text
NOTICE: delta_restore table=auth_processing phase=classify_nk_table start
NOTICE: delta_restore table=auth_processing phase=classify_nk_table done elapsed_ms=1234.567
```

Preview mode tees these notices to the console and saves them in `classification.err`.

## Selection grammar

Preview writes a default `selection.conf` like:

```text
# classes: new | changed | changed_local_newer   (others are never applyable)
[*] include=new,changed
[corp_processing] include=new,changed # new=12 changed=4 changed_local_newer=1
[bar_corps] include=                  # exclude this table entirely
```

Precedence:

1. `--selection-file <path>`
2. `--include-classes` / `--exclude-classes`
3. Default `new,changed`

Examples:

```bash
# Apply only NEW rows for all preserved tables.
./delta_restore_extract.sh --dump keep.dump --mode apply --include-classes new --yes

# Apply default classes except CHANGED rows.
./delta_restore_extract.sh --dump keep.dump --mode apply --exclude-classes changed --yes

# Only stamp corp-bearing rows for listed corps. Parent lookup tables are not restricted.
./delta_restore_extract.sh --dump keep.dump --mode apply --only-corps corps.txt --yes
```

`--tables a,b,c` narrows the default/CLI selection set. Staging and classification still run for the full preserved set so parent maps exist.

## Blocked-row remediation

If apply exits with code `4`, inspect the run artifacts and the database diagnostics before retrying:

```sql
SELECT * FROM delta_ctl.dependency_violations;
SELECT table_name, count_name, row_count FROM delta_ctl.run_counts
WHERE count_name IN ('BLOCKED_FK', 'BLOCKED_PARENT', 'AMBIGUOUS_NK')
ORDER BY table_name, count_name;
```

Common remediations:

- Include a required preserved parent class in `selection.conf`, or exclude the child class.
- Load/refresh missing external `corporation` or `event` rows before applying.
- Resolve duplicated natural keys in local data, or leave those rows unapplied.
- Regenerate the dump if a configured table was unintentionally absent.

## Recovery and cleanup

- Staging failures do not modify public tables.
- Apply failures inside the transaction roll back all public-table DML.
- Successful apply drops `delta_*` schemas unless `--keep-artifacts` is used.
- Interrupted or retained runs can be cleaned with:

```bash
./delta_restore_extract.sh --cleanup
```

## Advisory lock and concurrency

Delta restore uses the same PostgreSQL advisory-lock SQL as the subset/full-refresh scripts. This protects against cooperating maintenance scripts, but it does not stop unrelated app or migration-flow sessions. Avoid running migration flows against the target database during apply.

## DELTA_MODE removal

`DELTA_MODE=true ./restore_extract.sh` is intentionally unsupported. The full restore script aborts with a pointer to `data-tool/delta_restore_extract.sh` rather than running the old prototype branch or silently truncating. Use explicit preview/apply commands instead.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `2` | Preflight/schema drift/corrupt dump |
| `3` | Advisory lock busy/unavailable |
| `4` | Selection/dependency invalid |
| `5` | Apply verification failed; transaction rolled back |

## Tests

Run the lightweight harness from the repo root or `data-tool`:

```bash
make -C data-tool test-delta-restore
# or
data-tool/tests/delta_restore/run_tests.sh
```

The harness always runs shell/AWK static checks. PostgreSQL-backed compile/smoke scenarios run only when local `createdb`, `dropdb`, `psql`, `pg_dump`, and `pg_restore` are available and reachable with the current libpq environment.
