-- Delete a chunk of corps from the TARGET Postgres extract DB.
--
-- REQUIRED DbSchemaCLI variables (replace_variables=true):
--   corp_ids_in         : comma-separated SQL string literals for target corp_num values (NO parentheses),
--                         e.g. 'BC0460007','A1234567'
--
-- Intended to be executed from a master DbSchemaCLI script connected to the target Postgres DB (__DBSCHEMA_TARGET_SCHEMA__ schema).
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
DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.notification_resend
WHERE event_id IN (SELECT event_id FROM __DBSCHEMA_TARGET_SCHEMA__.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.notification
WHERE event_id IN (SELECT event_id FROM __DBSCHEMA_TARGET_SCHEMA__.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.filing_user
WHERE event_id IN (SELECT event_id FROM __DBSCHEMA_TARGET_SCHEMA__.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.payment
WHERE event_id IN (SELECT event_id FROM __DBSCHEMA_TARGET_SCHEMA__.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.ledger_text
WHERE event_id IN (SELECT event_id FROM __DBSCHEMA_TARGET_SCHEMA__.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.conv_ledger
WHERE event_id IN (SELECT event_id FROM __DBSCHEMA_TARGET_SCHEMA__.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.conv_event
WHERE event_id IN (SELECT event_id FROM __DBSCHEMA_TARGET_SCHEMA__.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.completing_party
WHERE event_id IN (SELECT event_id FROM __DBSCHEMA_TARGET_SCHEMA__.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.submitting_party
WHERE event_id IN (SELECT event_id FROM __DBSCHEMA_TARGET_SCHEMA__.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corp_involved_amalgamating
WHERE event_id IN (SELECT event_id FROM __DBSCHEMA_TARGET_SCHEMA__.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corp_involved_cont_in
WHERE event_id IN (SELECT event_id FROM __DBSCHEMA_TARGET_SCHEMA__.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.correction
WHERE event_id IN (SELECT event_id FROM __DBSCHEMA_TARGET_SCHEMA__.event WHERE corp_num IN (&corp_ids_in));

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.filing
WHERE event_id IN (SELECT event_id FROM __DBSCHEMA_TARGET_SCHEMA__.event WHERE corp_num IN (&corp_ids_in));

-- Delete corp-party related tables.
DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.party_notification
WHERE party_id IN (SELECT corp_party_id FROM __DBSCHEMA_TARGET_SCHEMA__.corp_party WHERE corp_num IN (&corp_ids_in));

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.offices_held
WHERE corp_party_id IN (SELECT corp_party_id FROM __DBSCHEMA_TARGET_SCHEMA__.corp_party WHERE corp_num IN (&corp_ids_in));

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corp_party_relationship
WHERE corp_party_id IN (SELECT corp_party_id FROM __DBSCHEMA_TARGET_SCHEMA__.corp_party WHERE corp_num IN (&corp_ids_in));

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corp_party
WHERE corp_num IN (&corp_ids_in);

-- Delete corp-scoped tables.
DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.office
WHERE corp_num IN (&corp_ids_in);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corp_name
WHERE corp_num IN (&corp_ids_in);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corp_state
WHERE corp_num IN (&corp_ids_in);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corp_comments
WHERE corp_num IN (&corp_ids_in);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corp_flag
WHERE corp_num IN (&corp_ids_in);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.cont_out
WHERE corp_num IN (&corp_ids_in);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corp_restriction
WHERE corp_num IN (&corp_ids_in);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.jurisdiction
WHERE corp_num IN (&corp_ids_in);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.resolution
WHERE corp_num IN (&corp_ids_in);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.share_series
WHERE corp_num IN (&corp_ids_in);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.share_struct_cls
WHERE corp_num IN (&corp_ids_in);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.share_struct
WHERE corp_num IN (&corp_ids_in);

-- Delete events last (many tables reference event_id).
DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.event
WHERE corp_num IN (&corp_ids_in);

-- Delete the corp rows last.
DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corporation
WHERE corp_num IN (&corp_ids_in);

-- Address rows are refreshed via stage+merge in subset_transfer_chunk.sql.
