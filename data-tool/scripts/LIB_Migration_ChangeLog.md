# Libraries (LIB) Migration - Change Log

## Overview

Data Mapping findings and code/SQL changes needed to migrate Library
entities from COLIN Oracle to LEAR Business DB and Auth DB.

---

## 1. COLIN Extract Script Changes

### File: `data-tool/scripts/transfer_cprd_corps.sql` → copied as `transfer_cprd_lib_only.sql`

**Entity Type Filter**

- Libraries `corp_type_cd` in COLIN/LEAR: **`LIB`**
- Replaced `('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')` with
  `('LIB')` across all 32 occurrences in `transfer_cprd_lib_only.sql`.

**Optional Tables - All Empty (0 rows) for Libraries**

| Table                | Join path to corp_type_cd                            | Row count |
| -------------------- | ---------------------------------------------------- | --------- |
| `share_struct`       | direct `corp_num`                                    | 0         |
| `cont_out`           | direct `corp_num`                                    | 0         |
| `corp_restriction`   | direct `corp_num`                                    | 0         |
| `resolution`         | direct `corp_num`                                    | 0         |
| `share_struct_cls`   | direct `corp_num`                                    | 0         |
| `share_series`       | direct `corp_num`                                    | 0         |
| `submitting_party`   | `event_id` → `event.corp_num`                        | 0         |
| `party_notification` | `party_id` → `corp_party.corp_party_id` → `corp_num` | 0         |
| `correction`         | `event_id` → `event.corp_num`                        | 0         |

Commented out all 9 of these transfer blocks in `transfer_cprd_lib_only.sql`
(`share_struct`, `share_struct_cls`, `share_series`, `submitting_party`, `party_notification`,
`cont_out`, `corp_restriction`, `correction`, `resolution`).

**Optional Change: Trimmed `address` Transfer UNION**

- Removed 2 UNION branches referencing `submitting_party` and `party_notification`.

**Commented Out CARS Transfers (4 tables)**

Commented out the 4 CARS-related transfer blocks in `transfer_cprd_lib_only.sql`:

- `transfer public.carsfile from cprd using ...`
- `transfer public.carsbox from cprd using ...`
- `transfer public.carsrept from cprd using ...`
- `transfer public.carindiv from cprd using ...`

**Why:** These 4 CARS tables (`carsfile`, `carsbox`, `carsrept`, `carindiv`) have **no primary key
and no unique constraint** in the staging DB DDL. Each `transfer ... from cprd using` statement is
a pure INSERT - running it a second time on an already-loaded staging DB would **silently duplicate
every row** (no error, no warning, just doubled data). Since the RLY POC run already loaded the
full CARS tables globally (the source query is `select ... from carsfile` with no `WHERE` clause),
re-running the LIB transfer would have doubled every RLY-era CARS row.

**Impact on LIB:** None. Libraries have 0 `conv_ledger` rows (verified during inventory), and the
tombstone flow only reads CARS data via `conv_ledger.cars_docmnt_id`. Skipping these 4 transfers
loses nothing for the LIB cohort.

---

## 2. Filing/Event Type Mapping

Queried `event`/`filing` joined to `corporation` for `corp_typ_cd = 'LIB'`:

| filing_typ_cd | event_typ_cd | count | Status                                      |
| ------------- | ------------ | ----- | ------------------------------------------- |
| OTAMA         | CONVOTHER    | 96    | Already mapped (`amalgamationApplication`)  |
| OTDIS         | FILE         | 69    | **New**                                     |
| OTINC         | CONVOTHER    | 13    | Already mapped (`incorporationApplication`) |
| OTNCN         | FILE         | 7     | **New**                                     |
| OTDIS         | CONVOTHER    | 3     | **New**                                     |

- `FILE_OTDIS` / `CONVOTHER_OTDIS` → `['dissolution', 'voluntary']`, display "Dissolution".
- `FILE_OTNCN` → `'changeOfName'`, display "Notice of Change of Name". New mapping.

---

## 3. Tombstone / Auth Flow Changes / Scripts Changes

- `flows/tombstone/tombstone_mappings.py` — added `FILE_OTDIS`, `CONVOTHER_OTDIS`, `FILE_OTNCN` to
  the `EventFilings` enum, `EVENT_FILING_LEAR_TARGET_MAPPING`, and
  `EVENT_FILING_DISPLAY_NAME_MAPPING` (see Section 2).
- `flows/tombstone/tombstone_queries.py` — added `'LIB'` to `corp_type_filter` (both occurrences,
  lines 106 and 232).
- `flows/auth/auth_queries.py` — added `'LIB'` to `CORP_TYPE_FILTER` (line 18).
- `flows/batch_delete_flow.py` — added `'LIB'` to the `legal_type IN (...)` allowlist in
  `businesses_cnt_query` and `identifiers_query`, so LIB test businesses cleaned-up
- `scripts/generate_cprd_subset_extract.py` — added `'LIB'` directly to the default
  `supported_types` list in `sql_render_oracle_corp_type_predicate`.

### `flows/tombstone/tombstone_utils.py` - Populate firstname/middlename/lastname in `format_users_data()`

Added 3 lines to copy the name fields from the COLIN source row `x` into the LEAR user dict:

```python
# BEFORE (lines 768-776):
user = {
    **user,
    'username': username,
    'email': x['u_email_addr'],
    'creation_date': x['earliest_event_dt_str']
}

# AFTER:
user = {
    **user,
    'username': username,
    'firstname': x.get('u_first_name'),       # NEW
    'middlename': x.get('u_middle_name'),      # NEW
    'lastname': x.get('u_last_name'),          # NEW
    'email': x['u_email_addr'],
    'creation_date': x['earliest_event_dt_str']
}
```

**Why this matters:**

The `format_users_data()` function builds the LEAR `users` row from a COLIN source row `x`.
The `**user` spread only brings in the **keys** from the `USER` template (defined in
`tombstone_base_data.py`), with the template's **default values** (all `None`). It does NOT
auto-populate from `x`.

Before the fix, the function overrode `username`, `email`, and `creation_date` from `x`, but
**never copied `firstname`/`middlename`/`lastname`** from COLIN - so they stayed `None` from the
template and got written as `NULL` to LEAR's `users` table, even when COLIN had real names.

**This bug was hiding behind the RLY POC** - the 3 RLY staff users happened to have NULL names in COLIN itself, so the bug was invisible. The fix matters
for any future migration with normal (non-staff) filing users that have real names in COLIN.

**Impact on LIB:** No-op. LIB has 0 filing users and 0 staff comment users, so
`format_users_data()` processes 0 records. The fix is still correct to apply (it doesn't break
anything) and matters for future POCs (CP, S, etc.) and production migrations with named users.

---

## 4. Next Steps

TBD
