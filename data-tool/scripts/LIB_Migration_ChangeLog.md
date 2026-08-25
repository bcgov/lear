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

| Table               | Join path to corp_type_cd                          | Row count |
| ------------------- | --------------------------------------------------- | --------- |
| `share_struct`      | direct `corp_num`                                    | 0         |
| `cont_out`          | direct `corp_num`                                    | 0         |
| `corp_restriction`  | direct `corp_num`                                    | 0         |
| `resolution`        | direct `corp_num`                                    | 0         |
| `share_struct_cls`  | direct `corp_num`                                    | 0         |
| `share_series`      | direct `corp_num`                                    | 0         |
| `submitting_party`  | `event_id` → `event.corp_num`                        | 0         |
| `party_notification`| `party_id` → `corp_party.corp_party_id` → `corp_num` | 0         |
| `correction`        | `event_id` → `event.corp_num`                        | 0         |

Commented out all 9 of these transfer blocks in `transfer_cprd_lib_only.sql`
(`share_struct`, `share_struct_cls`, `share_series`, `submitting_party`, `party_notification`,
`cont_out`, `corp_restriction`, `correction`, `resolution`).

**Optional Change: Trimmed `address` Transfer UNION**

- Removed 2 UNION branches referencing `submitting_party` and `party_notification`.

## 2. Filing/Event Type Mapping

Queried `event`/`filing` joined to `corporation` for `corp_typ_cd = 'LIB'`:

| filing_typ_cd | event_typ_cd | count | Status |
| --- | --- | --- | --- |
| OTAMA | CONVOTHER | 96 | Already mapped (`amalgamationApplication`) |
| OTDIS | FILE | 69 | **New** |
| OTINC | CONVOTHER | 13 | Already mapped (`incorporationApplication`) |
| OTNCN | FILE | 7 | **New** |
| OTDIS | CONVOTHER | 3 | **New** |

- `FILE_OTDIS` / `CONVOTHER_OTDIS` → `['dissolution', 'voluntary']`, display "Dissolution".
- `FILE_OTNCN` → `'changeOfName'`, display "Notice of Change of Name". New mapping.

## 3. Tombstone / Auth Flow Changes

- `flows/tombstone/tombstone_mappings.py` — added `FILE_OTDIS`, `CONVOTHER_OTDIS`, `FILE_OTNCN` to
  the `EventFilings` enum, `EVENT_FILING_LEAR_TARGET_MAPPING`, and
  `EVENT_FILING_DISPLAY_NAME_MAPPING` (see Section 2).
- `flows/tombstone/tombstone_queries.py` — added `'LIB'` to `corp_type_filter` (both occurrences,
  lines 106 and 232).
- `flows/auth/auth_queries.py` — added `'LIB'` to `CORP_TYPE_FILTER` (line 18).

## 4. Next Steps

TBD
