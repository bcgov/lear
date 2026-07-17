# Delta restore for preserved COLIN extract tables

`data-tool/delta_restore_extract.sh` merges a preserved-table dump into an existing COLIN PostgreSQL extract database without truncating preserved tables. Use it when a developer/local extract already has migration, tracking, or auth side-table data that must be reconciled with a newer preserved-table dump.

The preserved table set and phase order are centralized in `data-tool/scripts/restore/preserved_tables.conf`. The same file is consumed by:

- `data-tool/backup_extract_tables.sh` — creates the preserved-table dump and sidecar manifest.
- `data-tool/restore_extract.sh` — full restore path.
- `data-tool/delta_restore_extract.sh` — delta preview, validate, and apply path.

## Quick reference

### Contents

- [Golden path: merge a delta dump end to end](#golden-path-merge-a-delta-dump-end-to-end)
- [Connection and environment](#connection-and-environment)
- [Run directory artifacts](#run-directory-artifacts)
- [Modes: preview, validate, apply](#modes-preview-validate-apply)
- [Class semantics](#class-semantics)
- [Selection manifest and cookbook](#selection-manifest-and-cookbook)
  - [Row-selector grammar](#row-selector-grammar)
  - [Binding and validation](#binding-and-validation)
- [CLI and environment reference](#cli-and-environment-reference)
- [Detail artifacts and viewing](#detail-artifacts-and-viewing)
- [Querying the staged run directly](#querying-the-staged-run-directly)
- [Troubleshooting by exit code](#troubleshooting-by-exit-code)
- [Recovery, cleanup, and concurrency](#recovery-cleanup-and-concurrency)
- [DELTA_MODE removal and restore_extract.sh delegation](#delta_mode-removal-and-restore_extractsh-delegation)
- [Exit codes](#exit-codes)
- [Tests](#tests)

The five-command path, run from `data-tool/`, is:

```bash
# 1. Back up the preserved tables on the source.
PGDATABASE=source_extract BACKUP_DIR=/tmp/preserved ./backup_extract_tables.sh

# Export the target connection inherited by preview and its printed follow-up commands.
export PGDATABASE=local_extract

# 2. Preview against the target; keep the final "Artifacts:" path.
DUMP=/tmp/preserved/keep_$(date +%F).dump; ./delta_restore_extract.sh --dump "$DUMP" --mode preview

# 3. Set RUN to the printed path (example shown), then copy and edit the selection.
RUN=scripts/generated/delta_restore/20260716_183022; cp "$RUN/selection.conf" my_selection.conf; vi my_selection.conf

# 4. Validate the copy until this exits 0.
./delta_restore_extract.sh --dump "$DUMP" --mode validate --selection-file my_selection.conf

# 5. Paste the apply command printed by validate (shown here in full).
./delta_restore_extract.sh --dump "$DUMP" --mode apply --selection-file my_selection.conf --yes
```

> After a run directory is initialized, the invocation prints `Artifacts: <run-dir>` on success or `Artifacts retained for inspection: <run-dir>` on failure. Parse/help failures before initialization do not print an artifact path. Capture the preview path as `RUN` for review and selection editing; validate and apply each print their own diagnostic run directory.

## Golden path: merge a delta dump end to end

This walkthrough supplies every command and handoff needed for a normal merge. Follow links only when you need additional detail.

### Step 0: Prepare the target and connection

The target extract database must already exist with the current `colin_corps_extract_postgres_ddl` applied. Stop migration flows and avoid other non-cooperating writers against the target while applying. Export the target's [libpq settings](#connection-and-environment), at minimum `PGDATABASE`; set `PG_BIN` explicitly if the PostgreSQL client tools are not available through `PATH`.

Export the target connection so the preview command and its printed validate/apply follow-ups inherit the same database, then run the remaining commands from `data-tool/`:

```bash
export PGDATABASE=local_extract
cd data-tool
```

### Step 1: Create the dump on the source

```bash
PGDATABASE=source_extract \
BACKUP_DIR=/tmp/preserved \
./backup_extract_tables.sh
```

By default this creates `keep_YYYY-MM-DD.dump` under `BACKUP_DIR` and prints:

```text
✅  Wrote <dump> and <dump>.manifest.json
```

Keep the dump and sidecar together. Preview computes the dump sha256 and verifies it against the sidecar manifest.

### Step 2: Preview against the target

Use the exact dump path printed in Step 1:

```bash
DUMP=/tmp/preserved/keep_YYYY-MM-DD.dump
./delta_restore_extract.sh \
  --dump "$DUMP" \
  --mode preview
```

A successful run ends with a concrete path such as:

```text
Artifacts: scripts/generated/delta_restore/20260716_183022
```

Capture it:

```bash
RUN=scripts/generated/delta_restore/20260716_183022
```

`RUN` is the preview run directory used in Steps 3–4. The console also prints a ready-to-paste validate command for Step 5.

### Step 3: Review the preview in order

1. Read `$RUN/preview.txt` for class counts, per-table samples, and the detail index with rendered/total/truncation state.
2. Read the blast-radius comment immediately after `[*]` in `$RUN/selection.conf` for the number of rows selected by default.
3. For surprising counts, open `$RUN/details/<table>.<class>.txt`; its canonical `.tsv` is beside it.
4. For large or targeted reviews, use the recipes in [Querying the staged run directly](#querying-the-staged-run-directly).

### Step 4: Copy, then edit, the selection

Do not edit the generated manifest in place:

```bash
cp "$RUN/selection.conf" my_selection.conf
vi my_selection.conf
```

Copying keeps the generated manifest pristine for later diffing and keeps the run directory immutable. The copy retains the dump and staged-count binding headers required by validate/apply. The full grammar and 13 worked examples are in `$RUN/selection_cookbook.txt`. For `id:` selectors, use staged IDs from `selector_id`—never local-database IDs; see [Row-selector grammar](#row-selector-grammar).

### Step 5: Validate; repeat until exit 0

```bash
./delta_restore_extract.sh \
  --dump "$DUMP" \
  --mode validate \
  --selection-file my_selection.conf
```

Validate normally takes seconds because it reuses the resident preview instead of restaging. After each attempt, use that invocation's printed artifact path:

- Exit `4`: read `selection_diagnostics.tsv` and `dependency_violations.tsv` in the new validate run directory, edit `my_selection.conf`, and retry.
- Exit `2`: the resident preview is missing, incomplete, or stale; rerun Step 2 before retrying.

On exit `0`, validate prints the exact apply command to paste, carrying forward the current selection and selector flags.

### Step 6: Apply

Paste validate's printed command. For the commands above it is equivalent to:

```bash
./delta_restore_extract.sh \
  --dump "$DUMP" \
  --mode apply \
  --selection-file my_selection.conf \
  --yes
```

Apply deliberately re-verifies the dump hash, restages, reclassifies, binds, stamps, and checks dependencies against current local data. A validate result that has become stale therefore cannot bypass the apply safety checks.

### Step 7: Confirm

Capture the successful apply's final `Artifacts: <apply-run-dir>` path and read `<apply-run-dir>/apply_summary.txt`. Confirm every row's `expected` count equals `affected`. The summary also records the touched tables; apply analyzes those tables and repairs their sequences. On success, the `delta_*` schemas are dropped unless `--keep-artifacts` was supplied.

### Step 8: Clean up only when needed

After diagnosing an abandoned preview or failed apply, drop the resident delta schemas:

```bash
PGDATABASE=local_extract ./delta_restore_extract.sh --cleanup
```

Cleanup does not remove any run directory.

## Connection and environment

The script passes these libpq settings to PostgreSQL tools. Export the target settings before preview so the printed validate/apply commands inherit the same connection:

```bash
PGHOST=localhost
PGPORT=5432
PGUSER=postgres
PGDATABASE=colin-mig-corps-test
PGPASSWORD=...        # optional; or use .pgpass
```

`PG_BIN` optionally names the directory containing PostgreSQL client tools. If it is unset or explicitly empty (`PG_BIN=""`), `psql`, `pg_restore`, and related clients are resolved through `PATH`. If it is nonempty, clients are resolved from that directory.

The default run-directory base is `data-tool/scripts/generated/delta_restore/`. `DUMP` can supply the archive path instead of `--dump`, and `LOCK_TIMEOUT_SECONDS` controls the advisory-lock wait. See the consolidated [CLI and environment reference](#cli-and-environment-reference) for all defaults.

## Run directory artifacts

Artifacts are written under `data-tool/scripts/generated/delta_restore/<UTC timestamp>/` by default. The process sets `umask 077`, so new run directories and files default to modes 700 and 600.

| Artifact | Purpose |
| --- | --- |
| `preview.txt` | Class samples plus an index of detail artifacts with rendered/total counts, truncation state, aligned paths, and viewing tips. |
| `selection.conf` | Concise active v2 manifest. Binding headers protect row selectors; class-only v1 files remain supported. |
| `selection_cookbook.txt` | Full selector grammar and 13 commented examples generated for the same run. |
| `details/<table>.new.tsv` | Canonical staged selector, row ordinal, and public-column values for NEW rows. |
| `details/<table>.changed.tsv` | Canonical local-to-dump changed-column records for CHANGED and CHANGED_LOCAL_NEWER rows. |
| `details/<table>.blocked.tsv` | Canonical staged values, block class, and reason. |
| `details/<table>.<class>.txt` | Derived fixed-width companion for double-click/editor review; never consumed by apply. |
| `classification.out/.err` | Classification stdout and timing notices. |
| `temp_stats.tsv` | Before/after PostgreSQL temp file and byte counters. |
| `selection_diagnostics.tsv` | Selector match counts and any validation problem. |
| `dependency_violations.tsv` | Selected-child/preserved-parent violations. |
| `selected_counts.tsv` | Counts selected by table and class. |
| `apply_transaction.err` | Apply transaction errors, including verification failures. |
| `apply_summary.txt` | Successful apply's expected/affected counts and touched-table summary. |

Preview samples replace LF, tab, CR, and ESC with visible markers (`␤`, `␉`, `␍`, `␛`) and sanitize other terminal controls. Review `preview.txt` first, then the selection blast radius, then table/class details. Every exit prints the applicable run-directory path; failure paths remain available for diagnosis.

## Modes: preview, validate, apply

### Preview mode

Preview is the default. It:

1. Computes the dump sha256 and verifies it against optional `<dump>.manifest.json` metadata.
2. Filters the dump TOC to the preserved table list.
3. Creates `delta_stage`, `delta_map`, `delta_diff`, and `delta_ctl`.
4. Streams data into staging with guarded COPY-target rewriting.
5. Runs schema-drift preflight.
6. Classifies staged rows and builds ID maps.
7. Writes the operator and diagnostic artifacts.

`--sample-size` controls only how many rows per class appear in the *Samples* section of `preview.txt` for each table. It does not cap detail files; `--details-limit` does that.

### Validate mode

Validate is the fast selection-editing loop. It requires the same target database and dump used by a preceding preview whose delta schemas are still resident. It:

1. Acquires the normal advisory lock.
2. Confirms the resident control/diff objects are complete.
3. Hashes `--dump` and compares it with the resident `dump_sha256`.
4. Reconstructs staged-count bindings from `delta_ctl.run_counts`.
5. Reuses the normal bind → verify → stamp → dependency-check → selected-count workflow.
6. Writes diagnostics in a new run directory and prints a ready-to-paste apply command.

Validate does **not** read the dump TOC, restage, reclassify, prompt, or modify public tables. Its transient selection/stamp state is replaced by the next preview or apply.

A valid selection exits `0`. A missing or incomplete resident run, unreadable dump, or resident/dump sha mismatch is stale/preflight state and exits `2`; rerun preview. Lock contention exits `3`. Binding, selector, or dependency errors exit `4` and retain `selection_diagnostics.tsv` or `dependency_violations.tsv`.

Validate is advisory rather than the correctness gate. Local public tables can change after preview without changing the dump sha, so validate can become optimistic. Apply intentionally repeats dump verification, staging, classification, binding, stamping, and dependency checks against current local data.

### Apply mode

Apply re-runs staging and classification fresh, stamps the requested selection, validates dependencies, and applies selected rows in one `REPEATABLE READ` transaction. It repairs sequences, analyzes touched tables, writes `apply_summary.txt`, and drops the delta schemas unless `--keep-artifacts` is supplied.

Apply requires `--yes` or an interactive `yes` confirmation. Expected-versus-affected mismatches exit `5` and roll back the transaction.

### Schema and run-directory lifecycle

| After… | `delta_*` schemas | Run directory |
| --- | --- | --- |
| Preview success | Resident | Retained |
| Preview failure | Absent, incomplete, or resident depending on the failure stage | Retained |
| Validate success or exit `4` | Existing resident run remains; selection state is transient | Retained |
| Validate exit `2` | Existing state is unchanged and may be absent, incomplete, stale, or for a different dump | Retained |
| Apply success | Dropped unless `--keep-artifacts` | Retained |
| Apply failure (exit `4` or `5`) | Resident; public DML is rolled back | Retained |
| `--cleanup` | Dropped | Untouched |

## Class semantics

| Class | Meaning | Applyable? |
| --- | --- | --- |
| `NEW` | No safe local match. A staged ID may be preserved or reallocated. | Yes, by default |
| `CHANGED` | Natural-key/hash match with a different payload; dump wins. | Yes, by default |
| `CHANGED_LOCAL_NEWER` | Local `last_modified` is newer. | Only when explicitly included |
| `UNCHANGED` | Staged and local compared values are equivalent. | No |
| `LOCAL_ONLY` | Local row has no staged match; count-only diagnostic. | No |
| `BLOCKED_FK` | Required external or preserved-parent FK cannot be resolved safely. | No |
| `BLOCKED_PARENT` | Child depends on a blocked or ambiguous preserved parent. | No |
| `AMBIGUOUS_NK` | Natural key is duplicated for an unenforced-NK table. | No |
| `SKIPPED_ABSENT` | Configured table is absent from the dump. | No |

Natural-key matching is hash-accelerated while retaining the null-safe residual check. `auth_component_operation` is append-only: novel hash-parent rows can be inserted, but changed updates are not applied.

Classification emits grep-friendly timing notices to the console and `classification.err`:

```text
NOTICE: delta_restore table=auth_processing phase=classify_nk_table start
NOTICE: delta_restore table=auth_processing phase=classify_nk_table done elapsed_ms=1234.567
```

## Selection manifest and cookbook

Preview writes a concise `selection.conf`. The generated shape is:

```text
# delta-selection v2
# dump_sha256=<sha256>
# staged bad_emails=3 mig_group=128 ...
# ...
# ACTIVE SELECTION
[*]          include=new,changed
# Default selection ([*] new,changed) currently matches 97342 rows across 9 tables (new=96105 changed=1237).

[mig_batch]  include=new,changed # new=3 changed=2 changed_local_newer=0 parents=mig_group
# ...

# Small NEW sets receive ready-to-uncomment suggestions:

# [bad_emails] Exact NEW set: rows=14 singletons=4 ranges=3
# [bad_emails] new.rows include=id:101-104,200-203
#   Range counts: 101-104 (4 rows), 200-203 (4 rows)
# [bad_emails] new.rows include=id:300-301
#   Range counts: 300-301 (2 rows)

# [bad_emails] new.rows include=id:401,500,700
# [bad_emails] new.rows include=id:900

# Small CHANGED sets receive ready-to-uncomment suggestions:

# [mig_batch] Exact CHANGED set: rows=3 singletons=1 ranges=1
# [mig_batch] changed.rows include=row:150-151
#   Range counts: 150-151 (2 rows)

# [mig_batch] changed.rows include=row:160

# Large CHANGED sets receive a useful pointer rather than no guidance:
# corp_processing has 4812 CHANGED rows; choose selector_id or corp values from:
# details/corp_processing.changed.tsv
# Example syntax:
# [corp_processing] changed.rows include=id:100,200-210
# [corp_processing] changed.rows include=corp:BC0000001,BC0000002

# Full selector grammar and 13 worked examples: selection_cookbook.txt (this run dir)
```

Operator cues:

- The blast-radius comment immediately after `[*]` totals the default-selected NEW and CHANGED rows before any edit.
- A per-table `parents=` suffix lists preserved parents. A selected NEW child whose preserved parent is also NEW requires that parent row to remain selected.
- By default, sets of 1–50 NEW or CHANGED rows receive exact commented `id:` or `row:` suggestions; the limit is inclusive and applies independently to each table/class set. The summary reports total rows, isolated singleton values, and consecutive ranges (a range counts as one run, not as its number of rows).
- Actual blank lines separate table blocks and, for mixed sets, separate the range selectors from singleton selectors. A range selector always remains directly adjacent to its `Range counts` comment.
- Long categories wrap at a soft maximum of 120 characters. Every wrapped line repeats the complete `[table] class.rows include=kind:` prefix, no token is split, and an indivisible prefix-plus-token may exceed the soft maximum. Singleton lists producing more than eight selector lines receive another actual blank line after every four lines for visual grouping. There is no continuation syntax.
- Repeated complete `include=` lines are unioned by the existing selector semantics. Uncomment every suggested line to select the entire summarized exact set; uncommenting only some lines deliberately selects only that subset.
- Sets above the resolved limit receive a pointer to the corresponding canonical TSV and table-aware examples. Set `--selector-suggestion-limit 0` to make every positive NEW/CHANGED set use this generic guidance.
- `CHANGED_LOCAL_NEWER` never receives ready-to-uncomment guidance because overwriting newer local values must stay deliberate.
- `selection_cookbook.txt` holds the complete, commented grammar/examples; it is generated with the manifest so the two cannot drift.

The three preview-output controls are independent: `--sample-size` affects only `preview.txt` samples, `--details-limit` caps detail TSV/TXT artifacts, and `--selector-suggestion-limit` controls only commented manifest assistance. A generic pointer can therefore refer to a detail file truncated by a lower `--details-limit`; the full staged data remains queryable. Changing the selector-suggestion limit never changes active selection or apply behavior.

To generate a conservative manifest that selects nothing until explicitly edited:

```bash
./delta_restore_extract.sh \
  --dump keep.dump \
  --mode preview \
  --manifest-default none
```

This emits empty wildcard and per-table `include=` rules plus a zero-row blast-radius total. The default remains `new,changed` for compatibility.

### Row-selector grammar

Class-only v1 files remain valid and do not require binding headers. Optional row lines use:

```text
[table] <class>.rows <include|exclude>=<kind>:<values>
```

- Classes are `new`, `changed`, or `changed_local_newer`; the class must also be enabled by a class line.
- `id:` selects non-negative staged primary-key integers and inclusive ranges.
- `row:` selects staging ordinals for PK-less tables with the same bigint grammar.
- `corp:` selects exact identifiers on corp-bearing tables.
- Multiple include lines union their matches; excludes subtract afterward.
- With excludes only, the enabled class remains selected except for matching rows.
- `--only-corps` is a final intersection and never widens selection.

> **`id:` values are staged (dump) primary keys** — the `selector_id` column in `details/<table>.new.tsv` / `.changed.tsv` and the `id …` shown in preview samples. They are never local-database IDs. When a staged ID collides with an unrelated local row, apply allocates a fresh local ID; the selector still refers to the staged value you reviewed.

Example:

```text
[*] include=new,changed
[mig_batch] include=new,changed
[mig_corp_account] include=new,changed
[mig_corp_account] new.rows exclude=id:23
[corp_processing] include=new,changed
[corp_processing] changed.rows include=corp:BC0000001,BC0000002
```

### Binding and validation

The dump sha256 is computed for every run. Any file containing a `.rows` line must retain the generated `# dump_sha256=` header. A `row:` selector also requires the generated staged-count binding for that table. Duplicate hash headers, duplicate table counts, non-decimal counts, and binding mismatches exit `4`.

Every selector must match at least one classified row after the `--only-corps` intersection. Unsupported selector kinds, selectors on disabled classes, duplicate staged primary keys, zero matches, and scalar multi-matches exit `4` with line-numbered entries in `selection_diagnostics.tsv`. Parent dependency failures are written to `dependency_violations.tsv`, including up to ten child selector IDs.

Use validate repeatedly while editing:

```bash
./delta_restore_extract.sh --dump keep.dump --mode validate \
  --selection-file my_selection.conf
```

A selection file supplies the authored candidate set. Explicit CLI filters are then enforced as a hard ceiling:

1. `--tables a,b,c` removes every candidate from other tables.
2. A supplied `--include-classes` removes candidates outside those classes.
3. `--exclude-classes` removes its classes after the include ceiling.
4. Row selectors and `--only-corps` can narrow the remaining candidates but never widen them.

With no selection file, the default candidate classes remain `new,changed` unless `--include-classes` changes them. With a selection file and no explicit table/class filters, the file retains its previous full authoring behavior. A generated `selection.conf` remains a full preserved-set review artifact, so after a filtered preview use the printed validate command: it carries the same filters, and validate/apply cannot re-enable file entries outside that scope. Staging and classification still use the full preserved set so parent maps exist.

## CLI and environment reference

### Flags

| Flag | Argument | Default | Effect and details |
| --- | --- | --- | --- |
| `--dump` | `<path>` | `DUMP`; otherwise required | Uses the named `pg_dump -Fc` archive for preview, validate, or apply. |
| `--mode` | `preview\|validate\|apply` | `preview` | Chooses staging/reporting, fast resident selection validation, or transactional apply; see [Modes](#modes-preview-validate-apply). |
| `--tables` | `all\|<csv>` | `all` | Hard selection ceiling, including with `--selection-file`; staging and classification still use every preserved table so parent maps exist. |
| `--include-classes` | `<csv>` | None | When supplied, limits candidates to these classes even with `--selection-file`; otherwise a file chooses its own classes. |
| `--exclude-classes` | `<csv>` | None | Removes classes after selection-file/include processing and cannot widen selection. |
| `--selection-file` | `<path>` | None | Supplies generated/edited candidates for validate or apply; explicit table/class filters remain a hard ceiling, and row selections retain their bindings. |
| `--only-corps` | `<path>` | None | Intersects selected corp-bearing rows with identifiers from the file and never widens selection; parent lookup tables are not restricted. |
| `--sample-size` | `<n>` | `20` | Sets rows per class in each table's `preview.txt` *Samples* section. It affects `preview.txt` only; the detail TSV/TXT row cap is `--details-limit`. |
| `--details-limit` | `<n>` | `10000` | Caps rows per table/class detail artifact. Full totals remain in `preview.txt` and `TRUNCATED` markers identify capped output. |
| `--selector-suggestion-limit` | `<n>` | `50` | Controls exact commented selector ranges independently for each NEW/CHANGED table-class set. Accepts decimal integers `0..100000` inclusive; `0` makes every positive set use generic TSV guidance. This is CLI-only and does not alter active selection. |
| `--no-aligned-details` | — | Aligned `.txt` enabled | Suppresses derived fixed-width `.txt` companions; canonical TSVs are still written. |
| `--align-width` | `<n>` | `40`; floor `6` | Sets the maximum aligned-detail cell width; values 1–5 are raised to 6. |
| `--manifest-default` | `new,changed\|none` | `new,changed` | Chooses the generated manifest's active wildcard selection; see the [conservative manifest example](#selection-manifest-and-cookbook). |
| `--report-dir` | `<dir>` | `data-tool/scripts/generated/delta_restore` | Changes the base directory under which the UTC timestamped run directory is created. |
| `--keep-artifacts` | — | Off | Retains `delta_*` schemas after a successful apply; run-directory files are retained regardless. |
| `--yes` | — | Off | Skips the interactive `yes` confirmation for apply. |
| `--cleanup` | — | Off | Drops `delta_stage`, `delta_map`, `delta_diff`, and `delta_ctl`, then exits; run directories are untouched. |
| `-h`, `--help` | — | — | Prints usage, flags, exit codes, environment settings, and artifact handoff lines. |

### Environment variables

| Variable | Default | Effect |
| --- | --- | --- |
| `PGHOST` | `localhost` | PostgreSQL server host used by libpq clients. |
| `PGPORT` | `5432` | PostgreSQL server port. |
| `PGUSER` | `postgres` | PostgreSQL user. |
| `PGDATABASE` | `colin-mig-corps-test` | Target database. |
| `PGPASSWORD` / `.pgpass` | None | Optional libpq password source. Prefer `.pgpass` where appropriate. |
| `PG_BIN` | Unset or empty (`PATH`) | Optional directory containing PostgreSQL client tools. A nonempty value resolves clients from that directory. |
| `DUMP` | Empty | Alternative to `--dump`; the CLI flag replaces it. |
| `LOCK_TIMEOUT_SECONDS` | `30` | Seconds to wait for the shared subset/full-refresh advisory lock before exit `3`. |

## Detail artifacts and viewing

Only interesting classes generate detail files; `UNCHANGED` and `LOCAL_ONLY` do not. The TSV is canonical and remains grep/awk/spreadsheet-importable. The `.txt` file is derived from it, is never parsed by validate/apply, and can be regenerated; if the two ever disagree, trust the TSV.

The aligned companion preserves the TSV's visible COPY escapes rather than unescaping data. It uses a per-cell width of 40 by default, a minimum of 6, a two-space gutter, and a clipped `…` marker. Change the cap with `--align-width <n>` or disable companions with `--no-aligned-details`.

Each aligned file ends with a footer such as:

```text
# rendered 812 of 812 CHANGED rows
# rendered 10000 of 97105 NEW rows — TRUNCATED
```

Canonical truncated TSVs end with `# TRUNCATED at <n> rows`; `preview.txt` repeats rendered/total values and `(TRUNCATED)`. Values use COPY-style tab/newline/backslash escaping and are capped at 8 KiB. Rows are ordered by staged primary key and then staging ordinal. For PK-less CHANGED rows, local display uses the classification-time `ctid`.

Viewing options:

- Double-click/open `details/<table>.<class>.txt` in a text editor and turn off word wrap.
- Use `column -s $'\t' -t < details/<table>.<class>.tsv | less -S`.
- Import the canonical TSV into a spreadsheet.
- Query the resident staged run directly for large or targeted reviews.

## Querying the staged run directly

Preview leaves the delta schemas installed. Run these recipes against the same target database before cleanup or a successful apply without `--keep-artifacts`.

Filter NEW `corp_processing` rows by corporation prefix:

```sql
SELECT s.*
FROM delta_diff.corp_processing_class AS d
JOIN delta_stage.corp_processing AS s USING (_delta_row_id)
WHERE d.class = 'NEW'
  AND s.corp_num LIKE 'BC08%'
ORDER BY d.staged_pk NULLS LAST, d._delta_row_id;
```

List changed columns for one staged row:

```sql
SELECT d.staged_pk, d._delta_row_id, changed.column_name
FROM delta_diff.corp_processing_class AS d
CROSS JOIN LATERAL unnest(d.changed_cols) AS changed(column_name)
WHERE d.class IN ('CHANGED', 'CHANGED_LOCAL_NEWER')
  AND d.staged_pk = 881
ORDER BY changed.column_name;
```

Count blocking reasons for one table:

```sql
SELECT d.class, d.block_reason, count(*) AS rows
FROM delta_diff.corp_processing_class AS d
WHERE d.class IN ('BLOCKED_FK', 'BLOCKED_PARENT', 'AMBIGUOUS_NK')
GROUP BY d.class, d.block_reason
ORDER BY d.class, rows DESC;
```

For cross-table totals, query `delta_ctl.run_counts`:

```sql
SELECT table_name, count_name, row_count
FROM delta_ctl.run_counts
WHERE count_name IN ('NEW', 'CHANGED', 'CHANGED_LOCAL_NEWER',
                     'BLOCKED_FK', 'BLOCKED_PARENT', 'AMBIGUOUS_NK')
ORDER BY table_name, count_name;
```

## Troubleshooting by exit code

Use the final `Artifacts:` or `Artifacts retained for inspection:` line to find the run directory named below.

### Exit 0: successful run

**Symptom:** The command completed successfully.

**Read:** For preview, read `preview.txt` and copy `selection.conf`. For validate, use the printed ready-to-paste apply command. For apply, read `apply_summary.txt` and confirm `expected` equals `affected`.

**Next step:** Continue at the corresponding next step in the [Golden path](#golden-path-merge-a-delta-dump-end-to-end). No remediation is required.

### Exit 2: preflight, drift, dump, or stale-preview failure

**Symptom:** Preflight rejected schema drift, an unreadable/corrupt dump, a manifest sha mismatch, or validate found no complete resident preview matching the dump.

**Read:** Start with console stderr and the retained run directory. Check `dump.sha256` and any copied `dump.manifest.json`, `toc.list`/TOC errors, `drift_dump_only.tsv`, and `drift_local_required.tsv` as applicable.

**Remediation:** Fix the connection or input, apply the current DDL when the dump contains newer columns, regenerate the dump when it lacks required columns, or restore the matching dump/manifest pair. Then rerun preview; validate cannot repair stale or missing resident state.

### Exit 3: advisory lock busy or unavailable

**Symptom:** The shared subset/full-refresh advisory lock was not acquired within `LOCK_TIMEOUT_SECONDS`.

**Read:** Read console stderr and `advisory_lock.err` in the retained run directory to distinguish contention from a connection/lock error.

**Remediation:** Let the cooperating subset/full-refresh/delta operation finish, or investigate an unexpected holder before retrying. Increase `LOCK_TIMEOUT_SECONDS` only when a longer wait is appropriate; its default is 30 seconds.

### Exit 4: invalid selection, binding, or dependency

If validate or apply exits `4`, inspect the run artifacts and resident diagnostics:

```sql
SELECT * FROM delta_ctl.selection_diagnostics WHERE problem IS NOT NULL;
SELECT * FROM delta_ctl.dependency_violations;
SELECT table_name, count_name, row_count
FROM delta_ctl.run_counts
WHERE count_name IN ('BLOCKED_FK', 'BLOCKED_PARENT', 'AMBIGUOUS_NK')
ORDER BY table_name, count_name;
```

Common remediations:

- Include the required preserved parent, or exclude the selected child.
- Load/refresh missing external `corporation` or `event` rows.
- Resolve duplicated natural keys locally, or leave ambiguous rows unapplied.
- Regenerate the dump if a configured table was unintentionally absent.
- Rerun preview if validate reports absent, incomplete, or stale resident state.

The file equivalents are `selection_diagnostics.tsv`, `dependency_violations.tsv`, and `selected_counts.tsv` in the retained run directory. Edit the copied selection—not the generated `selection.conf`—then validate again.

### Exit 5: apply verification failed

**Symptom:** `APPLY_VERIFICATION_FAILED` means an expected count differed from its affected count, or a selected NEW row had no allocated local ID. The transaction rolled back, so **no public data changed**; the `delta_*` schemas and run directory are retained.

**Read:** Start with `apply_transaction.err`, which durably records the table/class and expected/affected counts. The failed transaction also rolls back its writes to `delta_ctl.apply_counts`, so that table is not a post-failure count diagnostic. For a missing-ID failure, use this read-only resident query, replacing `<table>` with the table named by the error:

```sql
-- disposition of every selected NEW row that would insert without an ID:
SELECT s.id AS staged_id, d.class, d.selected, m.local_id, m.disposition
FROM delta_stage.<table> s
JOIN delta_diff.<table>_class d USING (_delta_row_id)
LEFT JOIN delta_map.<table>_id_map m ON m.staged_id = s.id
WHERE d.selected AND d.class = 'NEW' AND m.local_id IS NULL;
```

**Remediation:** Do not hand-edit `delta_map` or staged rows. Capture the error and query output, run `--cleanup`, address the underlying cause, and rerun from preview. If `disposition = 'NEW_REALLOCATED'` with `local_id IS NULL`, verify the target table's ID sequence is discoverable through `pg_get_serial_sequence()`. The current DDL associates sequences with `ALTER SEQUENCE … OWNED BY`; databases created from older DDL may need that association applied.

## Recovery, cleanup, and concurrency

Use the [schema lifecycle table](#schema-and-run-directory-lifecycle) to determine whether resident state should exist. Staging failures do not modify public tables, and apply failures inside the transaction roll back all public-table DML. Run directories are retained regardless of schema cleanup.

Delta restore uses the same PostgreSQL advisory lock as the subset/full-refresh scripts. This protects against cooperating maintenance scripts, not unrelated application or migration-flow sessions. Avoid non-cooperating writers during apply.

After capturing any diagnostics, clean up resident schemas with:

```bash
PGDATABASE=local_extract ./delta_restore_extract.sh --cleanup
```

## DELTA_MODE removal and restore_extract.sh delegation

`DELTA_MODE=true ./restore_extract.sh` is intentionally unsupported and aborts with a pointer to `data-tool/delta_restore_extract.sh`. For CLI compatibility, `restore_extract.sh --delta <delta-arguments>` delegates directly to `delta_restore_extract.sh` after removing `--delta`. Prefer explicit preview, validate, and apply commands in operator runbooks.

## Exit codes

| Code | Meaning and troubleshooting |
| --- | --- |
| `0` | Preview/apply succeeded, or validate found the selection valid. [Next steps](#exit-0-successful-run). |
| `2` | Preflight/schema drift/corrupt or unreadable dump; for validate, no complete matching resident preview. [Troubleshoot exit 2](#exit-2-preflight-drift-dump-or-stale-preview-failure). |
| `3` | Advisory lock busy or unavailable. [Troubleshoot exit 3](#exit-3-advisory-lock-busy-or-unavailable). |
| `4` | Selection binding, selector, or dependency invalid. [Troubleshoot exit 4](#exit-4-invalid-selection-binding-or-dependency). |
| `5` | Apply verification failed; transaction rolled back. [Troubleshoot exit 5](#exit-5-apply-verification-failed). |

## Tests

Run the broad harness from the repo root:

```bash
make -C data-tool test-delta-restore
data-tool/tests/delta_restore/run_tests.sh --integration
```

The always-on static suite covers shell syntax, guarded COPY rewriting, aligned rendering and footer semantics, CLI validation, manifest plumbing, v1/v2 parsing, bindings, and the validate/apply orchestration boundary. PostgreSQL smoke tests cover classification, performance, selection stamping, diagnostics, dependencies, unchanged TSV renderers, manifest structure (T16), and the exact cookbook (T17). Integration covers backup → preview → valid/invalid validate without restaging → apply, private artifacts, real detail truncation/counts, and dump-hash rejection.

PostgreSQL-backed checks are skipped only when the required local tools or server are unavailable. See `docs/plans/delta_restore_extract_test_plan.md` for the matrix and deferred manual checks.
