-- Compute BCOMPS-excluded corps ONCE in Postgres, then purge those corps from the corp-scoped COLIN extract tables.
--
-- This is intended to replace the repeated Oracle-side "excluded_corps" computation previously embedded in every
-- transfer query (subset_transfer_chunk.sql).
--
-- IMPORTANT:
-- - This script intentionally does NOT touch internal migration/processing tables (mig_*, corp_processing,
--   colin_tracking, affiliation_processing, etc). It only purges the corp-scoped COLIN extract tables
--   that are reloaded from Oracle.
-- - Because preserved processing/tracking tables still reference corporation/event rows, refresh mode must keep
--   FK enforcement suppressed across this purge window too (for example via replica_role, or by disabling
--   triggers on the preserved referencing tables too).
-- - This script avoids DO $$ blocks for DbSchemaCLI compatibility.
-- - The helper keyset tables are predeclared in the COLIN extract DDL and reused via TRUNCATE/INSERT.

-- 1) Build keysets

TRUNCATE TABLE __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corp_parties;
TRUNCATE TABLE __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_events;
TRUNCATE TABLE __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corps;

INSERT INTO __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corps (corp_num)
SELECT DISTINCT e.corp_num
FROM __DBSCHEMA_TARGET_SCHEMA__.event e
JOIN __DBSCHEMA_TARGET_SCHEMA__.filing f      ON f.event_id = e.event_id
JOIN __DBSCHEMA_TARGET_SCHEMA__.filing_user u ON u.event_id = e.event_id
WHERE e.corp_num IS NOT NULL
  AND u.user_id = 'BCOMPS'
  AND f.filing_type_cd IN ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC');

INSERT INTO __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_events (event_id)
SELECT DISTINCT e.event_id
FROM __DBSCHEMA_TARGET_SCHEMA__.event e
JOIN __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corps x ON x.corp_num = e.corp_num
WHERE e.event_id IS NOT NULL;

INSERT INTO __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corp_parties (corp_party_id)
SELECT DISTINCT cp.corp_party_id
FROM __DBSCHEMA_TARGET_SCHEMA__.corp_party cp
JOIN __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corps x ON x.corp_num = cp.corp_num
WHERE cp.corp_party_id IS NOT NULL;

-- 2) Purge (delete child tables first)

-- Event-scoped children
DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.notification_resend t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.notification t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.filing_user t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.payment t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.ledger_text t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.conv_ledger t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.conv_event t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.completing_party t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.submitting_party t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corp_involved_cont_in t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.correction t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.filing t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_events x
WHERE t.event_id = x.event_id;

-- corp_involved_amalgamating can reference corp_num via ted_corp_num/ting_corp_num as well as event_id.
-- Delete any rows where either side is excluded (covers non-event-owned references too).
DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corp_involved_amalgamating t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corps x
WHERE t.ted_corp_num = x.corp_num
   OR t.ting_corp_num = x.corp_num;

-- Corp-party related
DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.party_notification t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corp_parties x
WHERE t.party_id = x.corp_party_id;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.offices_held t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corp_parties x
WHERE t.corp_party_id = x.corp_party_id;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corp_party_relationship t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corp_parties x
WHERE t.corp_party_id = x.corp_party_id;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corp_party t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corp_parties x
WHERE t.corp_party_id = x.corp_party_id;

-- Corp-scoped tables
DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.office t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corp_name t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corp_state t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corp_comments t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corp_flag t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.cont_out t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corp_restriction t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.jurisdiction t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.resolution t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

-- Share tables (delete deepest first)
DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.share_series t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.share_struct_cls t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.share_struct t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

-- Events last (many tables reference event_id)
DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.event t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_events x
WHERE t.event_id = x.event_id;

-- Corporation last
DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corporation t
USING __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

-- 3) Cleanup helper tables
TRUNCATE TABLE __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corp_parties;
TRUNCATE TABLE __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_events;
TRUNCATE TABLE __DBSCHEMA_TARGET_SCHEMA__.subset_excluded_corps;
