-- Delete a chunk of corps from the TARGET Postgres extract DB.
--
-- REQUIRED DbSchemaCLI variables (replace_variables=true):
--   corp_ids_in         : comma-separated SQL string literals for target corp_num values (NO parentheses),
--                         e.g. 'BC0460007','A1234567'
--
-- Intended to be executed from a master DbSchemaCLI script connected to the target Postgres DB (cprd_pg).
--
-- Note: This script intentionally does NOT delete internal migration/processing tables (mig_*, corp_processing,
-- colin_tracking, affiliation_processing, etc). It only deletes the corp-scoped COLIN extract tables that are
-- reloaded from Oracle.

-- Capture address ids referenced by these corps BEFORE deleting corp rows.
-- We use a TEMP table so we can safely delete addresses after deleting all referencing rows.
DROP TABLE IF EXISTS pg_temp.tmp_subset_refresh_addr_ids;
CREATE TEMP TABLE tmp_subset_refresh_addr_ids (
    addr_id numeric(10) PRIMARY KEY
);

INSERT INTO tmp_subset_refresh_addr_ids (addr_id)
SELECT DISTINCT s.addr_id
FROM (
    SELECT cp.mailing_addr_id AS addr_id
    FROM corp_party cp
    WHERE cp.corp_num IN (&corp_ids_in) AND cp.mailing_addr_id IS NOT NULL

    UNION
    SELECT cp.delivery_addr_id AS addr_id
    FROM corp_party cp
    WHERE cp.corp_num IN (&corp_ids_in) AND cp.delivery_addr_id IS NOT NULL

    UNION
    SELECT o.mailing_addr_id AS addr_id
    FROM office o
    WHERE o.corp_num IN (&corp_ids_in) AND o.mailing_addr_id IS NOT NULL

    UNION
    SELECT o.delivery_addr_id AS addr_id
    FROM office o
    WHERE o.corp_num IN (&corp_ids_in) AND o.delivery_addr_id IS NOT NULL

    UNION
    SELECT cpl.mailing_addr_id AS addr_id
    FROM completing_party cpl
    JOIN event e ON e.event_id = cpl.event_id
    WHERE e.corp_num IN (&corp_ids_in) AND cpl.mailing_addr_id IS NOT NULL

    UNION
    SELECT sp.mailing_addr_id AS addr_id
    FROM submitting_party sp
    JOIN event e ON e.event_id = sp.event_id
    WHERE e.corp_num IN (&corp_ids_in) AND sp.mailing_addr_id IS NOT NULL

    UNION
    SELECT sp.notify_addr_id AS addr_id
    FROM submitting_party sp
    JOIN event e ON e.event_id = sp.event_id
    WHERE e.corp_num IN (&corp_ids_in) AND sp.notify_addr_id IS NOT NULL

    UNION
    SELECT n.mailing_addr_id AS addr_id
    FROM notification n
    JOIN event e ON e.event_id = n.event_id
    WHERE e.corp_num IN (&corp_ids_in) AND n.mailing_addr_id IS NOT NULL

    UNION
    SELECT nr.mailing_addr_id AS addr_id
    FROM notification_resend nr
    JOIN event e ON e.event_id = nr.event_id
    WHERE e.corp_num IN (&corp_ids_in) AND nr.mailing_addr_id IS NOT NULL

    UNION
    SELECT pn.mailing_addr_id AS addr_id
    FROM party_notification pn
    JOIN corp_party cp ON cp.corp_party_id = pn.party_id
    WHERE cp.corp_num IN (&corp_ids_in) AND pn.mailing_addr_id IS NOT NULL
) s;

-- Delete child tables first (event-scoped).
DELETE FROM notification_resend
WHERE event_id IN (SELECT event_id FROM event WHERE corp_num IN (&corp_ids_in));

DELETE FROM notification
WHERE event_id IN (SELECT event_id FROM event WHERE corp_num IN (&corp_ids_in));

DELETE FROM filing_user
WHERE event_id IN (SELECT event_id FROM event WHERE corp_num IN (&corp_ids_in));

DELETE FROM payment
WHERE event_id IN (SELECT event_id FROM event WHERE corp_num IN (&corp_ids_in));

DELETE FROM ledger_text
WHERE event_id IN (SELECT event_id FROM event WHERE corp_num IN (&corp_ids_in));

DELETE FROM conv_ledger
WHERE event_id IN (SELECT event_id FROM event WHERE corp_num IN (&corp_ids_in));

DELETE FROM conv_event
WHERE event_id IN (SELECT event_id FROM event WHERE corp_num IN (&corp_ids_in));

DELETE FROM completing_party
WHERE event_id IN (SELECT event_id FROM event WHERE corp_num IN (&corp_ids_in));

DELETE FROM submitting_party
WHERE event_id IN (SELECT event_id FROM event WHERE corp_num IN (&corp_ids_in));

DELETE FROM corp_involved_amalgamating
WHERE event_id IN (SELECT event_id FROM event WHERE corp_num IN (&corp_ids_in));

DELETE FROM corp_involved_cont_in
WHERE event_id IN (SELECT event_id FROM event WHERE corp_num IN (&corp_ids_in));

DELETE FROM correction
WHERE event_id IN (SELECT event_id FROM event WHERE corp_num IN (&corp_ids_in));

DELETE FROM filing
WHERE event_id IN (SELECT event_id FROM event WHERE corp_num IN (&corp_ids_in));

-- Delete corp-party related tables.
DELETE FROM party_notification
WHERE party_id IN (SELECT corp_party_id FROM corp_party WHERE corp_num IN (&corp_ids_in));

DELETE FROM offices_held
WHERE corp_party_id IN (SELECT corp_party_id FROM corp_party WHERE corp_num IN (&corp_ids_in));

DELETE FROM corp_party_relationship
WHERE corp_party_id IN (SELECT corp_party_id FROM corp_party WHERE corp_num IN (&corp_ids_in));

DELETE FROM corp_party
WHERE corp_num IN (&corp_ids_in);

-- Delete corp-scoped tables.
DELETE FROM office
WHERE corp_num IN (&corp_ids_in);

DELETE FROM corp_name
WHERE corp_num IN (&corp_ids_in);

DELETE FROM corp_state
WHERE corp_num IN (&corp_ids_in);

DELETE FROM corp_comments
WHERE corp_num IN (&corp_ids_in);

DELETE FROM corp_flag
WHERE corp_num IN (&corp_ids_in);

DELETE FROM cont_out
WHERE corp_num IN (&corp_ids_in);

DELETE FROM corp_restriction
WHERE corp_num IN (&corp_ids_in);

DELETE FROM jurisdiction
WHERE corp_num IN (&corp_ids_in);

DELETE FROM resolution
WHERE corp_num IN (&corp_ids_in);

DELETE FROM share_series
WHERE corp_num IN (&corp_ids_in);

DELETE FROM share_struct_cls
WHERE corp_num IN (&corp_ids_in);

DELETE FROM share_struct
WHERE corp_num IN (&corp_ids_in);

-- Delete events last (many tables reference event_id).
DELETE FROM event
WHERE corp_num IN (&corp_ids_in);

-- Delete the corp rows last.
DELETE FROM corporation
WHERE corp_num IN (&corp_ids_in);

-- Delete addresses captured at the start (these will be reloaded from Oracle).
DELETE FROM address a
USING tmp_subset_refresh_addr_ids t
WHERE a.addr_id = t.addr_id;

DROP TABLE IF EXISTS pg_temp.tmp_subset_refresh_addr_ids;
