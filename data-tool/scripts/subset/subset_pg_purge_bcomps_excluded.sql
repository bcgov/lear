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

TRUNCATE TABLE public.subset_excluded_corp_parties;
TRUNCATE TABLE public.subset_excluded_events;
TRUNCATE TABLE public.subset_excluded_corps;

INSERT INTO public.subset_excluded_corps (corp_num)
SELECT DISTINCT e.corp_num
FROM event e
JOIN filing f      ON f.event_id = e.event_id
JOIN filing_user u ON u.event_id = e.event_id
WHERE e.corp_num IS NOT NULL
  AND u.user_id = 'BCOMPS'
  AND f.filing_type_cd IN ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC');

INSERT INTO public.subset_excluded_events (event_id)
SELECT DISTINCT e.event_id
FROM event e
JOIN public.subset_excluded_corps x ON x.corp_num = e.corp_num
WHERE e.event_id IS NOT NULL;

INSERT INTO public.subset_excluded_corp_parties (corp_party_id)
SELECT DISTINCT cp.corp_party_id
FROM corp_party cp
JOIN public.subset_excluded_corps x ON x.corp_num = cp.corp_num
WHERE cp.corp_party_id IS NOT NULL;

-- 2) Purge (delete child tables first)

-- Event-scoped children
DELETE FROM notification_resend t
USING public.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM notification t
USING public.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM filing_user t
USING public.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM payment t
USING public.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM ledger_text t
USING public.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM conv_ledger t
USING public.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM conv_event t
USING public.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM completing_party t
USING public.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM submitting_party t
USING public.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM corp_involved_cont_in t
USING public.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM correction t
USING public.subset_excluded_events x
WHERE t.event_id = x.event_id;

DELETE FROM filing t
USING public.subset_excluded_events x
WHERE t.event_id = x.event_id;

-- corp_involved_amalgamating can reference corp_num via ted_corp_num/ting_corp_num as well as event_id.
-- Delete any rows where either side is excluded (covers non-event-owned references too).
DELETE FROM corp_involved_amalgamating t
USING public.subset_excluded_corps x
WHERE t.ted_corp_num = x.corp_num
   OR t.ting_corp_num = x.corp_num;

-- Corp-party related
DELETE FROM party_notification t
USING public.subset_excluded_corp_parties x
WHERE t.party_id = x.corp_party_id;

DELETE FROM offices_held t
USING public.subset_excluded_corp_parties x
WHERE t.corp_party_id = x.corp_party_id;

DELETE FROM corp_party_relationship t
USING public.subset_excluded_corp_parties x
WHERE t.corp_party_id = x.corp_party_id;

DELETE FROM corp_party t
USING public.subset_excluded_corp_parties x
WHERE t.corp_party_id = x.corp_party_id;

-- Corp-scoped tables
DELETE FROM office t
USING public.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM corp_name t
USING public.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM corp_state t
USING public.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM corp_comments t
USING public.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM corp_flag t
USING public.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM cont_out t
USING public.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM corp_restriction t
USING public.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM jurisdiction t
USING public.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM resolution t
USING public.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

-- Share tables (delete deepest first)
DELETE FROM share_series t
USING public.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM share_struct_cls t
USING public.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

DELETE FROM share_struct t
USING public.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

-- Events last (many tables reference event_id)
DELETE FROM event t
USING public.subset_excluded_events x
WHERE t.event_id = x.event_id;

-- Corporation last
DELETE FROM corporation t
USING public.subset_excluded_corps x
WHERE t.corp_num = x.corp_num;

-- 3) Cleanup helper tables
TRUNCATE TABLE public.subset_excluded_corp_parties;
TRUNCATE TABLE public.subset_excluded_events;
TRUNCATE TABLE public.subset_excluded_corps;
