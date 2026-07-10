-- Delete a chunk of corps from the TARGET Postgres extract DB.
--
-- REQUIRED DbSchemaCLI variables (replace_variables=true):
--   corp_ids_in         : comma-separated SQL string literals for target corp_num values (NO parentheses),
--                         e.g. 'BC0460007','A1234567'
--
-- Intended to be executed from a master DbSchemaCLI script connected to the target Postgres DB (colin_extract schema).
--
-- Note: This script intentionally does NOT delete internal migration/processing tables (mig_*, corp_processing,
-- colin_tracking, affiliation_processing, etc). It only deletes the corp-scoped COLIN extract tables that are
-- reloaded from Oracle.
-- IMPORTANT:
-- - Because preserved processing/tracking tables still reference corporation/event rows, refresh mode must keep
--   FK enforcement suppressed across this delete/reload window (for example via replica_role, or by disabling
--   triggers on the preserved referencing tables too).

-- Address rows are treated as shared/global during subset refresh.
-- Do not delete them here: subset_transfer_chunk.sql stages incoming Oracle address rows and
-- merges them into the configured target address table by addr_id.

-- Delete child tables first (event-scoped).
DELETE FROM colin_extract.notification_resend
WHERE event_id IN (SELECT event_id FROM colin_extract.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM colin_extract.notification
WHERE event_id IN (SELECT event_id FROM colin_extract.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM colin_extract.filing_user
WHERE event_id IN (SELECT event_id FROM colin_extract.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM colin_extract.payment
WHERE event_id IN (SELECT event_id FROM colin_extract.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM colin_extract.ledger_text
WHERE event_id IN (SELECT event_id FROM colin_extract.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM colin_extract.conv_ledger
WHERE event_id IN (SELECT event_id FROM colin_extract.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM colin_extract.conv_event
WHERE event_id IN (SELECT event_id FROM colin_extract.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM colin_extract.completing_party
WHERE event_id IN (SELECT event_id FROM colin_extract.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM colin_extract.submitting_party
WHERE event_id IN (SELECT event_id FROM colin_extract.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM colin_extract.corp_involved_amalgamating
WHERE event_id IN (SELECT event_id FROM colin_extract.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM colin_extract.corp_involved_cont_in
WHERE event_id IN (SELECT event_id FROM colin_extract.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM colin_extract.correction
WHERE event_id IN (SELECT event_id FROM colin_extract.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM colin_extract.filing
WHERE event_id IN (SELECT event_id FROM colin_extract.event WHERE corp_num IN (&corp_ids_in));

-- Delete corp-party related tables.
DELETE FROM colin_extract.party_notification
WHERE party_id IN (SELECT corp_party_id FROM colin_extract.corp_party WHERE corp_num IN (&corp_ids_in));

DELETE FROM colin_extract.offices_held
WHERE corp_party_id IN (SELECT corp_party_id FROM colin_extract.corp_party WHERE corp_num IN (&corp_ids_in));

DELETE FROM colin_extract.corp_party_relationship
WHERE corp_party_id IN (SELECT corp_party_id FROM colin_extract.corp_party WHERE corp_num IN (&corp_ids_in));

DELETE FROM colin_extract.corp_party
WHERE corp_num IN (&corp_ids_in);

-- Delete corp-scoped tables.
DELETE FROM colin_extract.office
WHERE corp_num IN (&corp_ids_in);

DELETE FROM colin_extract.corp_name
WHERE corp_num IN (&corp_ids_in);

DELETE FROM colin_extract.corp_state
WHERE corp_num IN (&corp_ids_in);

DELETE FROM colin_extract.corp_comments
WHERE corp_num IN (&corp_ids_in);

DELETE FROM colin_extract.corp_flag
WHERE corp_num IN (&corp_ids_in);

DELETE FROM colin_extract.cont_out
WHERE corp_num IN (&corp_ids_in);

DELETE FROM colin_extract.corp_restriction
WHERE corp_num IN (&corp_ids_in);

DELETE FROM colin_extract.jurisdiction
WHERE corp_num IN (&corp_ids_in);

DELETE FROM colin_extract.resolution
WHERE corp_num IN (&corp_ids_in);

DELETE FROM colin_extract.share_series
WHERE corp_num IN (&corp_ids_in);

DELETE FROM colin_extract.share_struct_cls
WHERE corp_num IN (&corp_ids_in);

DELETE FROM colin_extract.share_struct
WHERE corp_num IN (&corp_ids_in);

-- Delete events last (many tables reference event_id).
DELETE FROM colin_extract.event
WHERE corp_num IN (&corp_ids_in);

-- Delete the corp rows last.
DELETE FROM colin_extract.corporation
WHERE corp_num IN (&corp_ids_in);

-- Address rows are refreshed via stage+merge in subset_transfer_chunk.sql.
