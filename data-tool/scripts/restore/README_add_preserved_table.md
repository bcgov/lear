# Adding a preserved table (backup, full restore, and delta restore)

[Overview](README_add_preserved_table_overview.md) · [Quick reference](README_add_preserved_table_quickref.md) · **Full guide** · [Delta runbook](README_delta_restore.md)

This guide walks you through adding a new preserved table so it participates correctly in all three scripts:

- `data-tool/backup_extract_tables.sh` — dumps preserved tables to a custom-format archive.
- `data-tool/restore_extract.sh` — restores preserved-table data into a rebuilt extract database.
- `data-tool/delta_restore_extract.sh` — previews/validates/applies a merge of a preserved-table dump into an existing extract database.

Section 3 is the **golden path** for a simple table — if your table is standalone with a straightforward key, you can follow it top to bottom and stop. Section 5 covers every advanced pattern the codebase supports, each anchored to a live example table and the test that proves the behavior.

---

## 0. Scope: which dump this guide is about

This guide concerns the **preserved-table custom-format dump** created by `backup_extract_tables.sh`:

- `pg_dump -Fc` with one `--table=` selector per entry in `preserved_tables.conf`, plus `--no-owner --no-acl`.
- Output: `keep_YYYY-MM-DD.dump` and a `<dump>.manifest.json` sidecar (sha256, table list, pg_dump version). When the sidecar is present, delta preview verifies its dump hash. Keep the files together even though preview currently permits a missing sidecar.

It is **not** about `data-tool/dump_colin_extract_without_views.sh`, which produces a *whole-extract* tar archive excluding the derived view/materialized-view layer. That is a separate workflow; nothing in this guide applies to it.

## 1. Mental model

1. **`data-tool/scripts/colin_corps_extract_postgres_ddl` is the schema source of truth.** The backup archive technically contains schema objects (pg_dump without `--data-only` includes them), but **restore never uses them**: `restore_extract.sh` runs `pg_restore --section=data --data-only` into tables that must already exist from the current DDL. If your table isn't in the DDL, restore has nowhere to put the data.
2. **Delta restore copies your local DDL, not the dump's.** Stage shells are created as `LIKE public.<table> INCLUDING DEFAULTS`, and a schema-drift preflight compares dump columns against local columns — drift exits with code `2`, a missing local table fails stage-shell creation with a pointer at the DDL file. Current local DDL is a hard prerequisite.
3. **`preserved_tables.conf` grants membership only.** Backup and full restore read just the table name (column 1). Delta restore also reads `load_phase` and requires effective metadata in `delta_ctl.complete_table_config()`. A conf entry alone does *not* make delta restore work.
4. **Keep three delta registrations aligned.** Runtime classification uses `delta_ctl.complete_table_config()` (`scripts/restore/delta/10_functions.sql`). The mirrored seed entry and staging index in `delta_restore_extract.sh` are repository conventions that keep bootstrap metadata and performance support aligned with that effective config. Fixtures validate the registration.
5. **Use the supported sequence pattern.** For a surrogate ID, production DDL should declare an explicit sequence, a `nextval(...)` column default, and `ALTER SEQUENCE … OWNED BY`. The default lets full restore repair the sequence; ownership makes it discoverable through `pg_get_serial_sequence()` when delta restore must reallocate a colliding ID.

## 2. Decision tree

Answer these before touching any file; each answer routes you to a step or an advanced branch.

```
Q1. Surrogate integer id column?
    ├─ yes → you need sequence + default + OWNED BY in DDL  ......... §3 step 1
    └─ no  → no configured surrogate ID ............................ §5.1

Q2. Is the row-matching "natural key" enforced by the database
    (unique constraint or unique index on exactly that key)?
    ├─ yes → nk_enforced = true
    └─ no  → nk_enforced = false; duplicates classify AMBIGUOUS_NK .. §5.3

Q3. What shape is the natural key?
    ├─ plain columns .............. nk_cols + matching s./l. exprs .. §3 step 3
    ├─ normalized expressions ..... nk_*_exprs with nk_cols='{}' .... §5.2
    └─ includes a preserved-parent FK → asymmetric map_fk exprs ..... §5.4

Q4. Foreign keys?
    ├─ to another preserved table → fk_map internal entry + phase ... §5.4
    ├─ to corporation/event/etc. → fk_map "external:…" entry ........ §5.5
    └─ none → fk_map = '{}'

Q5. Has a last_modified column that should protect newer local edits?
    └─ yes → has_last_modified = true ............................... §5.6

Q6. Append-only audit child (rows identified by content, not key)?
    └─ yes → match_mode = 'hash_parent' ............................. §5.7
```

## 3. Golden path: a simple table end to end

Worked example: a hypothetical standalone table `demigrated_filings` with a surrogate `id`, a database-enforced unique `filing_id`, no FKs, and no `last_modified`. Substitute your table's names throughout. Eight steps; each names the exact file and location.

### Step 1 — DDL in `data-tool/scripts/colin_corps_extract_postgres_ddl`

Three placements in this one file.

**(a) Sequence**, in the sequence block at the top of the file (alongside `bad_emails_id_seq` etc.):

```sql
create sequence if not exists demigrated_filings_id_seq;

alter sequence demigrated_filings_id_seq owner to postgres;
```

**(b) Table**, with PK, the enforced natural key, and ownership:

```sql
create table if not exists demigrated_filings
(
    id          integer default nextval('demigrated_filings_id_seq'::regclass) not null
        constraint pk_demigrated_filings primary key,
    filing_id   integer not null
        constraint unq_demigrated_filings_filing_id unique,
    notes       varchar(600),
    create_date timestamp with time zone default current_timestamp not null
);

alter table demigrated_filings
    owner to postgres;
```

Index rule for the natural key: the NK must have a supporting index on the **local** table. Here the unique constraint on `filing_id` already provides one, so nothing more is needed. If your NK is *not* covered by a unique constraint (unenforced or composite keys), add one following the existing convention:

```sql
create index if not exists idx_demigrated_filings_delta_nk
    on demigrated_filings (filing_id);
```

(Live examples: `idx_mig_group_delta_nk`, `idx_bar_corps_delta_nk`, and the normalized `ux_bad_emails_email_normalized`.)

**(c) Sequence association**, in the terminal `ALTER SEQUENCE … OWNED BY` block at the end of the file:

```sql
ALTER SEQUENCE public.demigrated_filings_id_seq
    OWNED BY public.demigrated_filings.id;
```

This line makes `pg_get_serial_sequence('public.demigrated_filings','id')` resolve when delta restore must reallocate a colliding ID. The `nextval(...)` default is what generic full-restore sequence repair reads. Use this explicit sequence pattern in production DDL; identity columns are used only by the slim test fixtures.

### Step 2 — Membership in `data-tool/scripts/restore/preserved_tables.conf`

Add one line:

```text
demigrated_filings                 10
```

Phase rules (delta apply/classification order is `ORDER BY load_phase, table_name`; backup and full restore ignore the number entirely):

| Band | Current occupants | Use for |
|---|---|---|
| 10 | reference/exclusion tables (`bad_emails`, `bar_corps`, …) | standalone tables with no preserved-parent FKs |
| 20–40 | `mig_group` → `mig_batch` → `mig_corp_batch`/`mig_corp_account` | the migration hierarchy |
| 50 | `corp_processing`, `colin_tracking`, `auth_processing` | tracking tables referencing `mig_batch` |
| 60 | `auth_component_operation` | audit children of phase-50 tables |

- A child must have a **strictly higher** phase than every preserved parent it references.
- Same-phase tables must not depend on each other.
- Use increments of 10 to leave room.
- Do **not** expect the phase to fix FK ordering in full restore — full restore uses one multi-table `TRUNCATE … RESTART IDENTITY` plus `pg_restore --disable-triggers`; phases play no role there.

### Step 3 — Effective delta config in `delta_ctl.complete_table_config()`

File: `data-tool/scripts/restore/delta/10_functions.sql`, inside `complete_table_config()`. Add an `UPDATE` block alongside the existing per-table blocks:

```sql
UPDATE delta_ctl.table_config SET
  pk_col = 'id',
  nk_stage_exprs = ARRAY['s.filing_id'],
  nk_local_exprs = ARRAY['l.filing_id'],
  nk_cols = ARRAY['filing_id'],
  nk_enforced = true
WHERE table_name = 'demigrated_filings';
```

Two things to know about this function:

- **It resets every table first.** The function begins by resetting all rows to defaults (`pk_col = NULL`, `nk_enforced = false`, empty exprs, `fk_map = '{}'`, …) and re-derives each table. If a dumped table has no block here, classification fails because its NK expressions are empty. Because of the reset you only need to set non-default fields.
- **Reuse the local constants** (`c_stage_corp_num`, `c_stage_flow_name`, etc.) when your expressions match them, following the surrounding code style.

Field reference:

| Field | Meaning | Set when |
|---|---|---|
| `pk_col` | Surrogate PK column name | table has one; `NULL` when no surrogate ID is configured (§5.1) |
| `nk_stage_exprs` / `nk_local_exprs` | Matching expressions over staged (`s.`) and local (`l.`) rows | always, in the same order; asymmetric for mapped parents (§5.4) |
| `nk_cols` | Plain NK column names | key is raw columns. Also excludes those columns from CHANGED updates via `update_columns()`. Use `'{}'` for expression keys (§5.2) |
| `nk_enforced` | Key uniqueness is database-enforced | **only** if a unique constraint/index exists on exactly that key (§5.3) |
| `fk_map` | `{"fk_col":"parent_table"}` or `{"fk_col":"external:table.column"}` | table has FKs (§5.4 / §5.5) |
| `has_last_modified` | Enables `CHANGED_LOCAL_NEWER` protection | column exists and should guard local edits (§5.6) |
| `match_mode` | `'nk'` (default) or `'hash_parent'` | audit children only (§5.7) |
| `compare_ignore_cols` | Columns excluded from content comparison | e.g. `['id']` for hash-parent tables |

### Step 4 — Seed mirror in `delta_restore_extract.sh`

File: `data-tool/delta_restore_extract.sh`, function `seed_table_config()`, inside the `seed_table_config_metadata.sql` heredoc (before its closing `SQL` marker). The heredoc uses grouped `IN (...)` lists — extend the matching lists:

- Add `'demigrated_filings'` to the `SET pk_col = 'id' WHERE table_name IN (…)` list.
- Add `'demigrated_filings'` to the `SET nk_enforced = true WHERE table_name IN (…)` list.
- (Only if applicable) extend the `has_last_modified`, `match_mode`, and `fk_map` statements.

Relationship between step 3 and step 4: **keep them in sync; the SQL function is authoritative.** `complete_table_config()` resets and rewrites the config at the start of every classification run, so the values that actually drive classification come from step 3. The shell seed is the current convention for having sane metadata present the moment the control schemas are installed. Consolidating the two is deliberately out of scope here.

### Step 5 — Staging index in `create_stage_indexes()`

File: `data-tool/delta_restore_extract.sh`, function `create_stage_indexes()`. Add one line in the block of `add_stage_index` calls:

```bash
add_stage_index demigrated_filings idx_delta_stage_demigrated_filings_nk "filing_id"
```

The index must cover the staged NK columns and reproduce intrinsic normalization — e.g. `bad_emails` uses `"lower(btrim(email))"`. For a mapped parent term such as `map_fk(...)`, index the raw staged FK column, following `mig_batch`. Keep this performance-supporting index aligned with the effective config.

### Step 6 — Roll the DDL out to existing extract databases

New DBs get the table automatically from the DDL file. Existing DBs need the new statements applied (sequence, table, indexes, `OWNED BY`) before you run any of the three scripts against them:

- Full restore into a DB missing the table aborts at the multi-table `TRUNCATE`; keep DDL current.
- Before full restore, confirm the dump contains a `TABLE DATA` entry for every current roster table. An older dump can omit a newly registered table, leaving it truncated without replacement data.
- Delta preview against a DB missing the table dies at stage-shell creation with `apply the latest colin_corps_extract_postgres_ddl first`.
- Delta preview against a DB with an older column set exits `2` with `drift_dump_only.tsv` / `drift_local_required.tsv` in the run directory.

### Step 7 — Test fixtures

Files under `data-tool/tests/delta_restore/fixtures/`:

**(a) `minimal_schema.sql`** — add a `DROP TABLE IF EXISTS demigrated_filings CASCADE;` line to the drop block *and* a create block using the fixture convention (identity column instead of an explicit sequence):

```sql
CREATE TABLE demigrated_filings (
  id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  filing_id integer UNIQUE,
  notes text
);
```

Keep only the columns delta config, classification, and apply reference — the fixture is intentionally slimmer than the real DDL.

**(b) `t01_identical.sql`** — seed at least one row so the integration path exercises backup, staging, and `UNCHANGED` classification:

```sql
INSERT INTO demigrated_filings(id, filing_id, notes)
VALUES (1, 90001, 'seed');
```

**(c)** t13 (selector diagnostics) and t16 (selection manifest) enumerate tables in their fixtures — extend them **only** if your table introduces novel selector or manifest behavior (a new corp-bearing lookup path, a new no-surrogate-ID pattern, etc.). Ordinary tables don't need them.

### Step 8 — Validate

Run the runbook in [§7](#7-validation-runbook). Minimum bar: `make -C data-tool test-delta-restore` passes and the identical fixture reaches `UNCHANGED`. Add a divergent or source-only fixture when you need to prove NEW insertion, FK mapping, or ID reallocation.

---

## 4. Class semantics and merge behavior (quick reference)

Full operator semantics live in the [delta restore runbook](README_delta_restore.md); this is the one-line version plus the three invariants people ask about.

| Class | Meaning | Applyable? |
|---|---|---|
| `NEW` | No safe local match | yes (default) |
| `CHANGED` | NK match, different payload; dump wins | yes (default) |
| `CHANGED_LOCAL_NEWER` | NK match but local `last_modified` is newer | only when explicitly selected |
| `UNCHANGED` | Payloads equivalent | no |
| `LOCAL_ONLY` | Local row with no staged match (count-only) | no |
| `BLOCKED_FK` | External or preserved-parent FK can't be resolved | no |
| `BLOCKED_PARENT` | Parent is blocked/ambiguous | no |
| `AMBIGUOUS_NK` | Duplicate NK on an unenforced-key table | no |
| `SKIPPED_ABSENT` | Configured table absent from the dump | no |

Invariants:

1. **ID collisions are safe.** If a selected NEW row's staged `id` collides with an unrelated local row, apply allocates a fresh local ID from the table's sequence (`disposition = NEW_REALLOCATED`); collision-free IDs are preserved (`NEW_PRESERVED`). This is the mechanism that requires `pg_get_serial_sequence()` to resolve (§3 step 1c).
2. **Children can't outrun parents.** A selected NEW child whose preserved parent is also NEW requires that parent row to stay selected — `validate_dependencies()` fails the run (exit `4`, `dependency_violations.tsv`) otherwise.
3. **Delta restore never deletes.** `LOCAL_ONLY` rows are counted for diagnostics and left untouched.

---

## 5. Advanced branches

Each subsection: when it applies, what to configure differently from §3, the live exemplar to copy from, and the test that proves the behavior.

### 5.1 Tables without a configured surrogate ID

*Exemplars: `excluded_emails`, `bar_corps`, `corps_with_third_party`, `email_domain_groups` (natural PK, no surrogate).*

- DDL: no sequence, no `OWNED BY`, no `id` column. Skip §3 steps 1a/1c.
- Config: `pk_col` stays `NULL` (the reset default) — just don't set it.
- Consequences: no ID map is built; CHANGED updates target rows by classification-time `ctid`; row selectors in selection files use `row:` staging ordinals instead of `id:`.
- Fixture note: `email_domain_groups` and `excluded_emails` show the shapes in `minimal_schema.sql`.

### 5.2 Expression keys (normalized matching)

*Exemplar: `bad_emails` — key is `lower(btrim(email))`, enforced by `ux_bad_emails_email_normalized`.*

- Config: put the normalization in the expressions and leave `nk_cols` empty:

  ```sql
  nk_stage_exprs = ARRAY['lower(btrim(s.email))'],
  nk_local_exprs = ARRAY['lower(btrim(l.email))'],
  nk_cols = '{}',
  nk_enforced = true
  ```

- Why `nk_cols` still matters even when empty: it feeds `update_columns()`, which excludes NK columns from CHANGED updates. With `nk_cols = '{}'`, the underlying column (`email`) **is** updated on CHANGED — usually what you want for normalized keys, where the raw value can legitimately differ in case/whitespace.
- DDL: the enforced key must be a unique **expression index** matching the normalization exactly.
- Stage index (§3 step 5) must use the same expression: `"lower(btrim(email))"`.

### 5.3 Unenforced keys and ambiguity

*Exemplars: `bar_corps`, `corps_with_third_party`, the whole `mig_*` hierarchy. Proof: fixtures/asserts t09.*

- Hard rule: **`nk_enforced = true` requires a database-enforced unique constraint or index on exactly the NK.** Nothing else counts. When `nk_enforced = true`, `detect_ambiguity()` skips the table entirely — a false claim silently allows duplicate-key misclassification.
- With `nk_enforced = false`, duplicated NK values (staged or local side) classify as `AMBIGUOUS_NK` and are never applyable. This is safe-by-default behavior, not an error to eliminate: resolve the duplicates locally or leave those rows unapplied.
- Composite unenforced keys (`corps_with_third_party`: `corp_num, vendor`) work identically — list all columns in the same order in all three `nk_*` arrays.

### 5.4 Parent–child tables (preserved-parent FKs)

*Exemplars: `mig_group` (20) → `mig_batch` (30) → `mig_corp_batch` / `mig_corp_account` (40). Proof: t08 (blocked parents), t14 (dependency validation), t12 (parent+children apply).*

- Phase: child strictly above parent (§3 step 2).
- `fk_map`: internal entry per parent FK — `'{"mig_group_id":"mig_group"}'::jsonb`.
- **Asymmetric NK expressions** when the parent FK is part of the key. Staged parent IDs may be reallocated, so the stage side must translate through the ID map while the local side reads the raw column (copy `mig_batch`):

  ```sql
  nk_stage_exprs = ARRAY['delta_ctl.map_fk(''mig_group'', s.mig_group_id::bigint)', 's.name', 's.target_environment'],
  nk_local_exprs = ARRAY['l.mig_group_id', 'l.name', 'l.target_environment'],
  nk_cols = ARRAY['mig_group_id', 'name', 'target_environment']
  ```

- Behavior you get for free: children of blocked/ambiguous parents become `BLOCKED_FK`/`BLOCKED_PARENT`; the generated `selection.conf` annotates the table with `parents=…`; deselecting a NEW parent while keeping its NEW child fails validation (exit `4`).
- Apply rewrites the FK value itself via `insert_expr()` → `map_fk`, so reallocated parent IDs propagate into inserted children automatically.

### 5.5 External FKs (rows outside the preserved set)

*Exemplars: `corp_processing` (`corporation`, `event`), `colin_tracking`/`auth_processing` (`corporation`). Code: `detect_external_fk_blocking()`.*

- `fk_map` syntax: `"corp_num":"external:corporation.corp_num"`, `"failed_event_id":"external:event.event_id"`.
- Semantics: if the referenced local row is missing, the staged row classifies `BLOCKED_FK` with a `… not in local extract` reason. **External targets are never created** — the remediation is to load/refresh the missing `corporation`/`event` rows (e.g. via the subset workflow), then rerun preview.
- These FKs are checks only; no ID mapping or rewriting occurs for external targets.

### 5.6 `has_last_modified` and locally-newer protection

*Exemplars: `corp_processing`, `colin_tracking`, `auth_processing`.*

- Set `has_last_modified = true` only when the column exists **and** newer local edits should win by default.
- Effect: an NK match where `l.last_modified > s.last_modified` classifies `CHANGED_LOCAL_NEWER` instead of `CHANGED`. It is excluded from the default selection, and the generated manifest deliberately never emits ready-to-uncomment selectors for it — overwriting newer local values must be an explicit operator decision (`include=new,changed,changed_local_newer`); add row selectors only to narrow that set.
- Full restore is unaffected (truncate + reload replaces everything regardless).

### 5.7 Hash-parent audit children (append-only)

*Exemplar: `auth_component_operation` (phase 60, child of `auth_processing`). T10 proves `LOCAL_ONLY` scoping to matched parents.*

Use this mode for immutable audit/log rows identified by their content under a parent, not by a stable key.

- Config: `match_mode = 'hash_parent'`, `compare_ignore_cols = ARRAY['id']`, `fk_map = '{"auth_processing_id":"auth_processing"}'::jsonb`. No NK arrays.
- Semantics: staged rows are matched by `md5` content hash (all columns except `id` and the parent FK, plus the **mapped** parent ID). Novel rows insert as NEW; matching rows are UNCHANGED; **there is no UPDATE path** — `apply_table()` returns after inserts for this mode, by design.
- `LOCAL_ONLY` is scoped to matched parents only, so unrelated local audit rows don't inflate counts.
- Caveat: the hash expression currently enumerates `public.auth_component_operation` columns specifically (`auth_component_hash_expr`); adding a *second* hash-parent table requires generalizing that function — treat it as an implementation task, not a config-only change, and `classify_table()` will raise `unsupported hash_parent table` until you do.

---

## 6. Complex worked example

A hypothetical `filing_reconciliation` table: child of `mig_batch`, external corp FK, enforced composite key, `last_modified`. Modeled on `corp_processing` — copy that table's blocks and adjust. Phase **50**.

**DDL** (`colin_corps_extract_postgres_ddl`; sequence block, table, terminal `OWNED BY`):

```sql
create sequence if not exists filing_reconciliation_id_seq;
alter sequence filing_reconciliation_id_seq owner to postgres;

create table if not exists filing_reconciliation
(
    id               integer default nextval('filing_reconciliation_id_seq'::regclass) not null
        constraint pk_filing_reconciliation primary key,
    corp_num         varchar(10)  not null
        constraint fk_filing_reconciliation_corporation
            references corporation (corp_num),
    flow_name        varchar(100) not null,
    environment      varchar(25)  not null,
    mig_batch_id     integer
        constraint fk_filing_reconciliation_batch
            references mig_batch,
    processed_status varchar(25)  not null,
    last_error       varchar(1000),
    create_date      timestamp with time zone default current_timestamp not null,
    last_modified    timestamp with time zone default current_timestamp not null,
    constraint unq_filing_reconciliation
        unique (corp_num, flow_name, environment)
);

alter table filing_reconciliation owner to postgres;

-- terminal block:
ALTER SEQUENCE public.filing_reconciliation_id_seq
    OWNED BY public.filing_reconciliation.id;
```

The unique constraint covers the NK, so `nk_enforced = true` is licensed and no extra `idx_…_delta_nk` index is required.

**Conf** (`preserved_tables.conf`) — strictly above `mig_batch` (30):

```text
filing_reconciliation              50
```

**`complete_table_config()`** (reuse the function's `c_stage_corp_num`-style constants as the surrounding code does):

```sql
UPDATE delta_ctl.table_config SET
  pk_col = 'id',
  nk_stage_exprs = ARRAY['s.corp_num', 's.flow_name', 's.environment'],
  nk_local_exprs = ARRAY['l.corp_num', 'l.flow_name', 'l.environment'],
  nk_cols = ARRAY['corp_num', 'flow_name', 'environment'],
  nk_enforced = true,
  has_last_modified = true,
  fk_map = '{"mig_batch_id":"mig_batch","corp_num":"external:corporation.corp_num"}'::jsonb
WHERE table_name = 'filing_reconciliation';
```

Note the NK here does **not** include `mig_batch_id`, so the expressions stay symmetric. If your key *did* include the parent FK, use the asymmetric `map_fk` form from §5.4.

**Seed mirror** (`seed_table_config()` heredoc): add to the `pk_col`, `nk_enforced`, and `has_last_modified` `IN` lists, and add an `fk_map` statement mirroring the above.

**Stage index** (`create_stage_indexes()`):

```bash
add_stage_index filing_reconciliation idx_delta_stage_filing_reconciliation_nk "corp_num, flow_name, environment"
```

**Fixtures**: identity-column create in `minimal_schema.sql` (drop block + create, keeping `corp_num`/`flow_name`/`environment`/`mig_batch_id`/`processed_status`/`last_modified`), and a seed row in `t01_identical.sql` referencing the existing seeded `corporation` and `mig_batch` rows.

**What you get from this shape**: rows for corps missing locally → `BLOCKED_FK`; children of unselected NEW batches → dependency violations; locally edited rows with newer `last_modified` → `CHANGED_LOCAL_NEWER`, protected unless explicitly selected; colliding staged IDs → cleanly reallocated.

---

## 7. Validation runbook

Prerequisites: local PostgreSQL client tools (`PG_BIN=/path/to/bin` if not on `PATH`), a reachable server, and **throwaway databases only** — never validate against a shared extract DB. `<t>` = your table.

**7.1 Static + SQL smoke + integration harness** (from repo root; extends automatically to your table once fixtures are updated per §3 step 7):

```bash
make -C data-tool test-delta-restore
data-tool/tests/delta_restore/run_tests.sh --integration
```

Success: `Summary: N passed, 0 failed`. PostgreSQL-backed checks skip (with a message) if tooling/server is unavailable — a skip is not a pass for your change; run them somewhere Postgres is available.

**7.2 Clean-database DDL check** (proves the DDL file applies from scratch):

```bash
createdb -h localhost -p 5432 -U postgres -T template0 preserved-ddl-check
psql -h localhost -p 5432 -U postgres -d preserved-ddl-check \
  -f data-tool/scripts/colin_corps_extract_postgres_ddl
```

Success: no errors. For a table with a sequence-backed surrogate ID, confirm sequence discoverability (must return the sequence name, not NULL); otherwise skip this check:

```bash
psql -h localhost -p 5432 -U postgres -d preserved-ddl-check -qAt \
  -c "SELECT pg_get_serial_sequence('public.<t>', 'id');"
```

**7.3 Backup + archive inspection** (preserved custom dump; source DB has current DDL and a few rows in `<t>`):

```bash
PGDATABASE=<source-db> BACKUP_DIR=/tmp/preserved ./data-tool/backup_extract_tables.sh
pg_restore -l /tmp/preserved/keep_*.dump | grep -E "TABLE DATA public <t> "
```

Success: exactly one `TABLE DATA` line for `<t>`, and the manifest sidecar lists the table:

```bash
grep '"<t>"' /tmp/preserved/keep_*.dump.manifest.json
```

**7.4 Full restore round-trip** (target = a throwaway rebuilt extract with current DDL and the base `corporation`/`event` rows required by preserved-table external FKs):

```bash
DUMP=/tmp/preserved/keep_YYYY-MM-DD.dump PGDATABASE=<target-db> ./data-tool/restore_extract.sh
```

Verify row counts match the source. For a table with a sequence-backed surrogate ID, also verify the sequence is ahead of the data; otherwise skip the sequence query:

```bash
psql -d <target-db> -qAt -c "SELECT count(*) FROM public.<t>;"
psql -d <target-db> -qAt -c \
  "SELECT nextval(pg_get_serial_sequence('public.<t>','id')) > COALESCE(max(id),0) FROM public.<t>;"
```

Success: counts equal; the second query returns `t`. (The `nextval` consumes one value — this is a throwaway DB.)

**7.5 Delta golden path** (follow the [delta restore runbook](README_delta_restore.md) end to end against a throwaway local DB that has diverging data in `<t>`):

```bash
export PGDATABASE=<local-db>
cd data-tool
./delta_restore_extract.sh --dump "$DUMP" --mode preview
# capture RUN from the printed "Artifacts:" line; review preview.txt and selection.conf
cp "$RUN/selection.conf" my_selection.conf
./delta_restore_extract.sh --dump "$DUMP" --mode validate --selection-file my_selection.conf
# paste the printed apply command (equivalent to):
./delta_restore_extract.sh --dump "$DUMP" --mode apply --selection-file my_selection.conf --yes
```

Success checkpoints:

- Preview: `<t>` appears in class counts; `drift_dump_only.tsv` and `drift_local_required.tsv` are empty; expected NEW/CHANGED rows are visible in `details/<t>.*.tsv`.
- Validate: exit `0`, `Selection is valid`.
- Apply: aggregate `expected` and `affected` counts match for each table/class/action line; ID-map dispositions show `NEW_PRESERVED`/`NEW_REALLOCATED`/`MATCHED` as expected.

Failure routing: exit `2` → drift/DDL (§3 step 6); exit `4` → `selection_diagnostics.tsv` / `dependency_violations.tsv`; exit `5` → inspect `apply_transaction.err`. For a colliding NEW ID, also verify `OWNED BY` per §3 step 1c. See the [full exit-code table](README_delta_restore.md#exit-codes).

**7.6 FK and row-level spot checks** (after apply, for tables with FKs):

```bash
# no orphaned children (example for a mig_batch child):
psql -d <local-db> -qAt -c \
  "SELECT count(*) FROM public.<t> c LEFT JOIN public.mig_batch p ON p.id = c.mig_batch_id
   WHERE c.mig_batch_id IS NOT NULL AND p.id IS NULL;"
# selected counts vs actual delta:
cat "$RUN_APPLY/selected_counts.tsv"
```

Success: orphan count `0`; table deltas consistent with `selected_counts.tsv`.

**7.7 Cleanup**:

```bash
PGDATABASE=<local-db> ./delta_restore_extract.sh --cleanup
dropdb -h localhost -U postgres preserved-ddl-check <target-db> <local-db>
```
