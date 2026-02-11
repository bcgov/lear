-- Compute BCOMPS-excluded corps ONCE in Postgres, then purge those corps from the corp-scoped COLIN extract tables.
--
-- This is intended to replace the repeated Oracle-side "excluded_corps" computation previously embedded in every
-- transfer query (subset_transfer_chunk.sql).
--
-- IMPORTANT:
-- - This script intentionally does NOT touch internal migration/processing tables (mig_*, corp_processing,
--   colin_tracking, affiliation_processing, etc). It only purges the corp-scoped COLIN extract tables
--   that are reloaded from Oracle.
-- - This script avoids DO $$ blocks for DbSchemaCLI compatibility.

-- 1) Build keysets

DROP TABLE IF EXISTS pg_temp.excluded_corps;
CREATE TEMP TABLE excluded_corps AS
SELECT DISTINCT e.corp_num
FROM event e
JOIN filing f      ON f.event_id = e.event_id
JOIN filing_user u ON u.event_id = e.event_id
WHERE u.user_id = 'BCOMPS'
  AND f.filing_type_cd IN ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC');

CREATE INDEX ON pg_temp.excluded_corps (corp_num);

DROP TABLE IF EXISTS pg_temp.excluded_events;
CREATE TEMP TABLE excluded_events AS
SELECT e.event_id
FROM event e
JOIN pg_temp.excluded_corps x ON x.corp_num = e.corp_num;

CREATE INDEX ON pg_temp.excluded_events (event_id);

DROP TABLE IF EXISTS pg_temp.excluded_corp_parties;
CREATE TEMP TABLE excluded_corp_parties AS
SELECT cp.corp_party_id
FROM corp_party cp
JOIN pg_temp.excluded_corps x ON x.corp_num = cp.corp_num;

CREATE INDEX ON pg_temp.excluded_corp_parties (corp_party_id);

-- 2) Purge (delete child tables first)

-- Event-scoped children
DELETE FROM notification_resend t
USING pg_temp.excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM notification t
USING pg_temp.excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM filing_user t
USING pg_temp.excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM payment t
USING pg_temp.excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM ledger_text t
USING pg_temp.excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM conv_ledger t
USING pg_temp.excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM conv_event t
USING pg_temp.excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM completing_party t
USING pg_temp.excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM submitting_party t
USING pg_temp.excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM corp_involved_cont_in t
USING pg_temp.excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM correction t
USING pg_temp.excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM filing t
USING pg_temp.excluded_events x
WHERE t.event_id = x.event_id;

-- corp_involved_amalgamating can reference corp_num via ted_corp_num/ting_corp_num as well as event_id.
-- Delete any rows where either side is excluded (covers non-event-owned references too).
DELETE FROM corp_involved_amalgamating t
USING pg_temp.excluded_corps x
WHERE t.ted_corp_num = x.corp_num
   OR t.ting_corp_num = x.corp_num;

-- Corp-party related
DELETE FROM party_notification t
USING pg_temp.excluded_corp_parties x
WHERE t.party_id = x.corp_party_id;

DELETE FROM offices_held t
USING pg_temp.excluded_corp_parties x
WHERE t.corp_party_id = x.corp_party_id;

DELETE FROM corp_party_relationship t
USING pg_temp.excluded_corp_parties x
WHERE t.corp_party_id = x.corp_party_id;

DELETE FROM corp_party t
USING pg_temp.excluded_corp_parties x
WHERE t.corp_party_id = x.corp_party_id;

-- Corp-scoped tables
DELETE FROM office t
USING pg_temp.excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM corp_name t
USING pg_temp.excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM corp_state t
USING pg_temp.excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM corp_comments t
USING pg_temp.excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM corp_flag t
USING pg_temp.excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM cont_out t
USING pg_temp.excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM corp_restriction t
USING pg_temp.excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM jurisdiction t
USING pg_temp.excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM resolution t
USING pg_temp.excluded_corps x
WHERE t.corp_num = x.corp_num;

-- Share tables (delete deepest first)
DELETE FROM share_series t
USING pg_temp.excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM share_struct_cls t
USING pg_temp.excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM share_struct t
USING pg_temp.excluded_corps x
WHERE t.corp_num = x.corp_num;

-- Events last (many tables reference event_id)
DELETE FROM event t
USING pg_temp.excluded_events x
WHERE t.event_id = x.event_id;

-- Corporation last
DELETE FROM corporation t
USING pg_temp.excluded_corps x
WHERE t.corp_num = x.corp_num;

-- 3) Cleanup temp tables
DROP TABLE IF EXISTS pg_temp.excluded_corp_parties;
DROP TABLE IF EXISTS pg_temp.excluded_events;
DROP TABLE IF EXISTS pg_temp.excluded_corps;
