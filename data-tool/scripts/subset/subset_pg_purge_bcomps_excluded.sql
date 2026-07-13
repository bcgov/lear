-- Compute BCOMPS-excluded corps ONCE in Postgres, then purge those corps FROM TARGET_SCHEMA.the corp-scoped COLIN extract tables.
--
-- This is intended to replace the repeated Oracle-side "excluded_corps" computation previously embedded in every
-- transfer query (subset_transfer_chunk.sql).
--
-- IMPORTANT:
-- - This script intentionally does NOT touch internal migration/processing tables (mig_*, corp_processing,
--   colin_tracking, affiliation_processing, etc). It only purges the corp-scoped COLIN extract tables
--   that are reloaded FROM TARGET_SCHEMA.Oracle.
-- - Because preserved processing/tracking tables still reference corporation/event rows, refresh mode must keep
--   FK enforcement suppressed across this purge window too (for example via replica_role, or by disabling
--   triggers on the preserved referencing tables too).
-- - This script avoids DO $$ blocks for DbSchemaCLI compatibility.
-- - The helper keyset tables are predeclared in the COLIN extract DDL and reused via TRUNCATE/INSERT.

-- 1) Build keysets

TRUNCATE TABLE TARGET_SCHEMA.subset_excluded_corp_parties;
TRUNCATE TABLE TARGET_SCHEMA.subset_excluded_events;
TRUNCATE TABLE TARGET_SCHEMA.subset_excluded_corps;

INSERT INTO TARGET_SCHEMA.subset_excluded_corps (corp_num)
SELECT DISTINCT e.corp_num
FROM TARGET_SCHEMA.event e
JOIN TARGET_SCHEMA.filing f      ON f.event_id = e.event_id
JOIN TARGET_SCHEMA.filing_user u ON u.event_id = e.event_id
WHERE e.corp_num IS NOT NULL
  AND u.user_id = 'BCOMPS'
  AND f.filing_type_cd IN ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC');

INSERT INTO TARGET_SCHEMA.subset_excluded_events (event_id)
SELECT DISTINCT e.event_id
FROM TARGET_SCHEMA.event e
JOIN TARGET_SCHEMA.subset_excluded_corps x ON x.corp_num = e.corp_num
WHERE e.event_id IS NOT NULL;

INSERT INTO TARGET_SCHEMA.subset_excluded_corp_parties (corp_party_id)
SELECT DISTINCT cp.corp_party_id
FROM TARGET_SCHEMA.corp_party cp
JOIN TARGET_SCHEMA.subset_excluded_corps x ON x.corp_num = cp.corp_num
WHERE cp.corp_party_id IS NOT NULL;

-- 2) Purge (delete child tables first)

-- Event-scoped children
DELETE FROM TARGET_SCHEMA.notification_resend t
USING TARGET_SCHEMA.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM TARGET_SCHEMA.notification t
USING TARGET_SCHEMA.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM TARGET_SCHEMA.filing_user t
USING TARGET_SCHEMA.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM TARGET_SCHEMA.payment t
USING TARGET_SCHEMA.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM TARGET_SCHEMA.ledger_text t
USING TARGET_SCHEMA.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM TARGET_SCHEMA.conv_ledger t
USING TARGET_SCHEMA.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM TARGET_SCHEMA.conv_event t
USING TARGET_SCHEMA.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM TARGET_SCHEMA.completing_party t
USING TARGET_SCHEMA.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM TARGET_SCHEMA.submitting_party t
USING TARGET_SCHEMA.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM TARGET_SCHEMA.corp_involved_cont_in t
USING TARGET_SCHEMA.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM TARGET_SCHEMA.correction t
USING TARGET_SCHEMA.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM TARGET_SCHEMA.filing t
USING TARGET_SCHEMA.subset_excluded_events x
WHERE t.event_id = x.event_id;

-- corp_involved_amalgamating can reference corp_num via ted_corp_num/ting_corp_num as well as event_id.
-- Delete any rows where either side is excluded (covers non-event-owned references too).
DELETE FROM TARGET_SCHEMA.corp_involved_amalgamating t
USING TARGET_SCHEMA.subset_excluded_corps x
WHERE t.ted_corp_num = x.corp_num
   OR t.ting_corp_num = x.corp_num;

-- Corp-party related
DELETE FROM TARGET_SCHEMA.party_notification t
USING TARGET_SCHEMA.subset_excluded_corp_parties x
WHERE t.party_id = x.corp_party_id;

DELETE FROM TARGET_SCHEMA.offices_held t
USING TARGET_SCHEMA.subset_excluded_corp_parties x
WHERE t.corp_party_id = x.corp_party_id;

DELETE FROM TARGET_SCHEMA.corp_party_relationship t
USING TARGET_SCHEMA.subset_excluded_corp_parties x
WHERE t.corp_party_id = x.corp_party_id;

DELETE FROM TARGET_SCHEMA.corp_party t
USING TARGET_SCHEMA.subset_excluded_corp_parties x
WHERE t.corp_party_id = x.corp_party_id;

-- Corp-scoped tables
DELETE FROM TARGET_SCHEMA.office t
USING TARGET_SCHEMA.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM TARGET_SCHEMA.corp_name t
USING TARGET_SCHEMA.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM TARGET_SCHEMA.corp_state t
USING TARGET_SCHEMA.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM TARGET_SCHEMA.corp_comments t
USING TARGET_SCHEMA.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM TARGET_SCHEMA.corp_flag t
USING TARGET_SCHEMA.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM TARGET_SCHEMA.cont_out t
USING TARGET_SCHEMA.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM TARGET_SCHEMA.corp_restriction t
USING TARGET_SCHEMA.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM TARGET_SCHEMA.jurisdiction t
USING TARGET_SCHEMA.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM TARGET_SCHEMA.resolution t
USING TARGET_SCHEMA.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

-- Share tables (delete deepest first)
DELETE FROM TARGET_SCHEMA.share_series t
USING TARGET_SCHEMA.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM TARGET_SCHEMA.share_struct_cls t
USING TARGET_SCHEMA.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM TARGET_SCHEMA.share_struct t
USING TARGET_SCHEMA.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

-- Events last (many tables reference event_id)
DELETE FROM TARGET_SCHEMA.event t
USING TARGET_SCHEMA.subset_excluded_events x
WHERE t.event_id = x.event_id;

-- Corporation last
DELETE FROM TARGET_SCHEMA.corporation t
USING TARGET_SCHEMA.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

-- 3) Cleanup helper tables
TRUNCATE TABLE TARGET_SCHEMA.subset_excluded_corp_parties;
TRUNCATE TABLE TARGET_SCHEMA.subset_excluded_events;
TRUNCATE TABLE TARGET_SCHEMA.subset_excluded_corps;
