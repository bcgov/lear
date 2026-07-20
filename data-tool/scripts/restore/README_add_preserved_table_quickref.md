# Add a preserved table — quick reference

[Overview](README_add_preserved_table_overview.md) · **Quick reference** · [Full guide](README_add_preserved_table.md) · [Delta runbook](README_delta_restore.md)

One table in, six edits, three working scripts. Do the steps **top to bottom** — later steps assume earlier ones.

```
                          new table
                              │
        1  DDL          ──┬──►  backup ✓   full restore ✓
        2  conf line    ──┘
        3  delta config ──┐
        4  seed mirror    ├──►  delta restore ✓   (needs 1–5)
        5  stage index  ──┘
        6  fixtures     ─────►  automated validation
                              │
              run: backup ─► restore ─► delta preview/validate/apply
                              │
                  ✔ apply_summary: expected = affected
```

Two constants run through all six edits:
- the **table name** appears in every step (the final grep check counts on this);
- the **natural key** in the `nk_*` expressions and stage index must match. When `nk_enforced=true`, the DDL must also define the same key as unique.

Example table throughout: `demigrated_filings` (surrogate `id`, unique `filing_id`). Substitute your names.

---

### 1 ▸ DDL · `data-tool/scripts/colin_corps_extract_postgres_ddl` — three spots, one file

```sql
-- ① TOP (sequence block)
create sequence if not exists demigrated_filings_id_seq;
alter sequence demigrated_filings_id_seq owner to postgres;

-- ② BODY (table; the unique key here IS your delta "natural key" — steps 3 and 5 reuse it)
create table if not exists demigrated_filings (
    id        integer default nextval('demigrated_filings_id_seq'::regclass) not null
        constraint pk_demigrated_filings primary key,
    filing_id integer not null
        constraint unq_demigrated_filings_filing_id unique,
    notes     varchar(600)
);
alter table demigrated_filings owner to postgres;

-- ③ BOTTOM (association block) — required to reallocate colliding IDs
ALTER SEQUENCE public.demigrated_filings_id_seq OWNED BY public.demigrated_filings.id;
```

⚑ Restores are **data-only** — apply this DDL to every DB you'll run the scripts against, or the table simply isn't there to receive rows. (No surrogate `id`? Skip ① and ③.)

### 2 ▸ Conf · `data-tool/scripts/restore/preserved_tables.conf` — one line

```text
demigrated_filings                 10
```

Phase = delta ordering only (backup/full restore ignore it): **10** standalone · **20–40** mig hierarchy · **50** tables referencing `mig_batch` · **60** audit children. A child's phase must be **higher** than every preserved parent it references.

*Backup and full restore already work at this point — steps 3–6 are the delta half.*

### 3 ▸ Delta config · `complete_table_config()` in `data-tool/scripts/restore/delta/10_functions.sql`

**The template** — one `UPDATE` block next to the existing ones. Every line annotated; this is the simple case complete:

```sql
UPDATE delta_ctl.table_config SET
  pk_col = 'id',                           -- surrogate ID column (omit if none is configured)
  nk_stage_exprs = ARRAY['s.filing_id'],   -- match key, dump side  ─┐ same key, same order,
  nk_local_exprs = ARRAY['l.filing_id'],   -- match key, local side ─┤ = step 1's constraint
  nk_cols = ARRAY['filing_id'],            -- plain NK column names ─┘ = step 5's index
  nk_enforced = true                       -- true ONLY if a real unique constraint/index exists
WHERE table_name = 'demigrated_filings';   --   on exactly that key; else false → duplicates
                                           --   classify AMBIGUOUS_NK (the safe outcome)
```

**Not the simple case?** Apply the diff for your situation on top of the template — `+` add a line, `~` change a line, `−` drop a line. Situations **stack** (e.g. `corp_processing` = parent FK + external FK + last_modified). The named table is the live block in the same function — copy-check yours against it.

```diff
No configured surrogate ID                    check against: excluded_emails, bar_corps
- pk_col = 'id'                               (rows match/update by ctid; selectors use row:)

Normalized key (case/space-insensitive)       check against: bad_emails
~ nk_stage_exprs = ARRAY['lower(btrim(s.email))']
~ nk_local_exprs = ARRAY['lower(btrim(l.email))']
~ nk_cols = '{}'                              (steps 1 + 5 must use the SAME expression)

Child of a preserved table                    check against: mig_batch
+ fk_map = '{"mig_group_id":"mig_group"}'::jsonb
~ nk_stage_exprs FK term → delta_ctl.map_fk('mig_group', s.mig_group_id::bigint)
                                              (local side stays l.mig_group_id — asymmetry
                                               is deliberate: staged parent IDs get remapped.
                                               conf phase must be > the parent's)

References corporation / event                check against: corp_processing
+ fk_map entry → "corp_num":"external:corporation.corp_num"
                                              (missing target rows → BLOCKED_FK; never created)

Has a last_modified guard                     check against: corp_processing
+ has_last_modified = true                    (newer local rows → CHANGED_LOCAL_NEWER,
                                               protected unless explicitly selected)

Append-only audit child                       check against: auth_component_operation
+ match_mode = 'hash_parent'                  ⚠ NOT config-only — a 2nd hash_parent table
+ compare_ignore_cols = ARRAY['id']              needs code changes (hash fn is table-specific)
```

### 4 ▸ Seed mirror · `seed_table_config()` heredoc in `data-tool/delta_restore_extract.sh`

Add `'demigrated_filings'` to the `pk_col = 'id' … IN (…)` and `nk_enforced = true … IN (…)` lists (plus `fk_map` / `has_last_modified` if step 3 used them). Keep in sync with step 3; step 3 wins at classification time.

### 5 ▸ Stage index · `create_stage_indexes()` in `data-tool/delta_restore_extract.sh`

```bash
add_stage_index demigrated_filings idx_delta_stage_demigrated_filings_nk "filing_id"
```

⚑ Cover the staged NK columns and intrinsic normalization (for example, `"lower(btrim(email))"`). For `map_fk(...)`, index the raw staged FK column, following `mig_batch`.

### 6 ▸ Fixtures · `data-tool/tests/delta_restore/fixtures/`

`minimal_schema.sql` — add to the DROP block, then (identity form, per fixture convention):

```sql
CREATE TABLE demigrated_filings (
  id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  filing_id integer UNIQUE,
  notes text
);
```

`t01_identical.sql` — one seed row to exercise backup, staging, and `UNCHANGED` classification:

```sql
INSERT INTO demigrated_filings(id, filing_id, notes) VALUES (1, 90001, 'seed');
```

---

## Run to completion

Throwaway DBs only. `PG_BIN=/path/to/bin` if Postgres tools aren't on `PATH`.

```bash
# tests — expect "Summary: N passed, 0 failed" (skips ≠ passes)
make -C data-tool test-delta-restore
data-tool/tests/delta_restore/run_tests.sh --integration

# BACKUP (source DB)
PGDATABASE=<source-db> BACKUP_DIR=/tmp/preserved ./data-tool/backup_extract_tables.sh
DUMP=/tmp/preserved/keep_YYYY-MM-DD.dump                              # path printed by the backup
pg_restore -l "$DUMP" | grep "TABLE DATA public demigrated_filings "  # no match → recheck step 2
# Before full restore, confirm the dump has TABLE DATA for every current roster table.

# FULL RESTORE (rebuilt target that already has current DDL)
PGDATABASE=<target-db> DUMP="$DUMP" ./data-tool/restore_extract.sh
# ends "Done. Preserved tables restored; sequences synchronised." — table errors → recheck step 1

# DELTA (existing local DB with diverging rows)
export PGDATABASE=<local-db>; cd data-tool
./delta_restore_extract.sh --dump "$DUMP" --mode preview       # note printed "Artifacts: <RUN>"
cp <RUN>/selection.conf my.conf
./delta_restore_extract.sh --dump "$DUMP" --mode validate --selection-file my.conf
./delta_restore_extract.sh --dump "$DUMP" --mode apply --selection-file my.conf --yes
```

✔ **Done when** aggregate `expected` and `affected` counts match for each table/class/action line. The identical fixture should classify the seed as `UNCHANGED`; use a divergent or source-only fixture to prove NEW insertion, FK mapping, or ID reallocation.

Dot-check — the table name must appear in all six edits; a missing file = the step you skipped:

```bash
grep -rln demigrated_filings \
  data-tool/scripts/colin_corps_extract_postgres_ddl \
  data-tool/scripts/restore/preserved_tables.conf \
  data-tool/scripts/restore/delta/10_functions.sql \
  data-tool/delta_restore_extract.sh \
  data-tool/tests/delta_restore/fixtures/minimal_schema.sql \
  data-tool/tests/delta_restore/fixtures/t01_identical.sql
# expect all 6 files (delta_restore_extract.sh covers steps 4 AND 5 — name appears twice inside it)
```

## If it stops

```
exit 2 ............ dump/local columns disagree → step 1 not rolled out to this DB; fix, rerun preview
exit 4 ............ bad selection or NEW child without its NEW parent → selection_diagnostics.tsv /
                    dependency_violations.tsv in the printed run dir
exit 5 ............ inspect apply_transaction.err; for a colliding NEW ID, verify step 1③
                    (OWNED BY) on the target
AMBIGUOUS_NK ...... genuine duplicates on an unenforced key → resolve locally or leave unapplied;
                    never "fix" by setting nk_enforced=true without a real constraint
classification .... empty NK expression error → step 3 effective config block is missing
```

Deep dives: [golden path and exit codes](README_delta_restore.md) · [rationale, advanced patterns, and full runbook](README_add_preserved_table.md).
