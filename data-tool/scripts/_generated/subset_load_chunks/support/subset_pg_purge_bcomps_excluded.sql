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

TRUNCATE TABLE colin_extract.subset_excluded_corp_parties;
TRUNCATE TABLE colin_extract.subset_excluded_events;
TRUNCATE TABLE colin_extract.subset_excluded_corps;

INSERT INTO colin_extract.subset_excluded_corps (corp_num)
SELECT DISTINCT e.corp_num
FROM colin_extract.event e
JOIN colin_extract.filing f      ON f.event_id = e.event_id
JOIN colin_extract.filing_user u ON u.event_id = e.event_id
WHERE e.corp_num IS NOT NULL
  AND u.user_id = 'BCOMPS'
  AND f.filing_type_cd IN ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC');

INSERT INTO colin_extract.subset_excluded_events (event_id)
SELECT DISTINCT e.event_id
FROM colin_extract.event e
JOIN colin_extract.subset_excluded_corps x ON x.corp_num = e.corp_num
WHERE e.event_id IS NOT NULL;

INSERT INTO colin_extract.subset_excluded_corp_parties (corp_party_id)
SELECT DISTINCT cp.corp_party_id
FROM colin_extract.corp_party cp
JOIN colin_extract.subset_excluded_corps x ON x.corp_num = cp.corp_num
WHERE cp.corp_party_id IS NOT NULL;

-- 2) Purge (delete child tables first)

-- Event-scoped children
DELETE FROM colin_extract.notification_resend t
USING colin_extract.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM colin_extract.notification t
USING colin_extract.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM colin_extract.filing_user t
USING colin_extract.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM colin_extract.payment t
USING colin_extract.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM colin_extract.ledger_text t
USING colin_extract.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM colin_extract.conv_ledger t
USING colin_extract.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM colin_extract.conv_event t
USING colin_extract.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM colin_extract.completing_party t
USING colin_extract.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM colin_extract.submitting_party t
USING colin_extract.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM colin_extract.corp_involved_cont_in t
USING colin_extract.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM colin_extract.correction t
USING colin_extract.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM colin_extract.filing t
USING colin_extract.subset_excluded_events x
WHERE t.event_id = x.event_id;

-- corp_involved_amalgamating can reference corp_num via ted_corp_num/ting_corp_num as well as event_id.
-- Delete any rows where either side is excluded (covers non-event-owned references too).
DELETE FROM colin_extract.corp_involved_amalgamating t
USING colin_extract.subset_excluded_corps x
WHERE t.ted_corp_num = x.corp_num
   OR t.ting_corp_num = x.corp_num;

-- Corp-party related
DELETE FROM colin_extract.party_notification t
USING colin_extract.subset_excluded_corp_parties x
WHERE t.party_id = x.corp_party_id;

DELETE FROM colin_extract.offices_held t
USING colin_extract.subset_excluded_corp_parties x
WHERE t.corp_party_id = x.corp_party_id;

DELETE FROM colin_extract.corp_party_relationship t
USING colin_extract.subset_excluded_corp_parties x
WHERE t.corp_party_id = x.corp_party_id;

DELETE FROM colin_extract.corp_party t
USING colin_extract.subset_excluded_corp_parties x
WHERE t.corp_party_id = x.corp_party_id;

-- Corp-scoped tables
DELETE FROM colin_extract.office t
USING colin_extract.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM colin_extract.corp_name t
USING colin_extract.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM colin_extract.corp_state t
USING colin_extract.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM colin_extract.corp_comments t
USING colin_extract.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM colin_extract.corp_flag t
USING colin_extract.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM colin_extract.cont_out t
USING colin_extract.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM colin_extract.corp_restriction t
USING colin_extract.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM colin_extract.jurisdiction t
USING colin_extract.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM colin_extract.resolution t
USING colin_extract.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

-- Share tables (delete deepest first)
DELETE FROM colin_extract.share_series t
USING colin_extract.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM colin_extract.share_struct_cls t
USING colin_extract.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM colin_extract.share_struct t
USING colin_extract.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

-- Events last (many tables reference event_id)
DELETE FROM colin_extract.event t
USING colin_extract.subset_excluded_events x
WHERE t.event_id = x.event_id;

-- Corporation last
DELETE FROM colin_extract.corporation t
USING colin_extract.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

-- 3) Cleanup helper tables
TRUNCATE TABLE colin_extract.subset_excluded_corp_parties;
TRUNCATE TABLE colin_extract.subset_excluded_events;
TRUNCATE TABLE colin_extract.subset_excluded_corps;
