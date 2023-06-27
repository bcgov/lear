-- ******************************************************************************************************************
-- Description:
-- Script that runs after transfer_to_new_lear.sql runs.
-- This script re-enables triggers and removes temporary triggers/columns/functions used to deal with transferring
-- enum type data.
--
-- Note: it would have been ideal to have the sql in this script in transfer_to_new_lear.sql but the tool(dbshell)
-- used to transfer data between the source(old LEAR) and target(new LEAR) database has issues with the postgres
-- enum type.  To workaround this enum issue, temporary triggers/columns/functions are used to populate the enum
-- fields properly.
-- ******************************************************************************************************************

-- Re-enable triggers
ALTER TABLE users
    ENABLE TRIGGER ALL;
ALTER TABLE users_history
    ENABLE TRIGGER ALL;
ALTER TABLE dc_definitions
    ENABLE TRIGGER ALL;
ALTER TABLE legal_entities
    ENABLE TRIGGER ALL;
ALTER TABLE legal_entities_history
    ENABLE TRIGGER ALL;
ALTER TABLE filings
    ENABLE TRIGGER ALL;
ALTER TABLE addresses
    ENABLE TRIGGER ALL;
ALTER TABLE addresses_history
    ENABLE TRIGGER ALL;
ALTER TABLE aliases
    ENABLE TRIGGER ALL;
ALTER TABLE aliases_history
    ENABLE TRIGGER ALL;
ALTER TABLE colin_event_ids
    ENABLE TRIGGER ALL;
ALTER TABLE colin_last_update
    ENABLE TRIGGER ALL;
ALTER TABLE comments
    ENABLE TRIGGER ALL;
ALTER TABLE dc_connections
    ENABLE TRIGGER ALL;
ALTER TABLE dc_definitions
    ENABLE TRIGGER ALL;
ALTER TABLE dc_issued_credentials
    ENABLE TRIGGER ALL;
ALTER TABLE documents
    ENABLE TRIGGER ALL;
ALTER TABLE documents_history
    ENABLE TRIGGER ALL;
ALTER TABLE offices
    ENABLE TRIGGER ALL;
ALTER TABLE offices_history
    ENABLE TRIGGER ALL;
ALTER TABLE parties
    ENABLE TRIGGER ALL;
ALTER TABLE parties_history
    ENABLE TRIGGER ALL;
ALTER TABLE party_roles
    ENABLE TRIGGER ALL;
ALTER TABLE party_roles_history
    ENABLE TRIGGER ALL;
ALTER TABLE registration_bootstrap
    ENABLE TRIGGER ALL;
ALTER TABLE request_tracker
    ENABLE TRIGGER ALL;
ALTER TABLE resolutions
    ENABLE TRIGGER ALL;
ALTER TABLE resolutions_history
    ENABLE TRIGGER ALL;
ALTER TABLE share_classes
    ENABLE TRIGGER ALL;
ALTER TABLE share_classes_history
    ENABLE TRIGGER ALL;
ALTER TABLE share_series
    ENABLE TRIGGER ALL;
ALTER TABLE share_series_history
    ENABLE TRIGGER ALL;
ALTER TABLE consent_continuation_outs
    ENABLE TRIGGER ALL;
ALTER TABLE sent_to_gazette
    ENABLE TRIGGER ALL;

-- Cleanup temporary columns/functions/triggers

-- legal_entities.state & legal_entities_history.state enum
DROP TRIGGER fill_state_trigger ON legal_entities;
DROP TRIGGER fill_state_history_trigger ON legal_entities_history;
ALTER TABLE legal_entities
    DROP COLUMN state_text;
ALTER TABLE legal_entities_history
    DROP COLUMN state_text;
DROP FUNCTION fill_state;

-- dc_definitions.credential_type enum
DROP TRIGGER fill_credential_type_trigger ON dc_definitions;
ALTER TABLE dc_definitions
    DROP COLUMN credential_type_text;
DROP FUNCTION fill_credential_type;

-- request_tracker.request_type enum
DROP TRIGGER fill_request_type_trigger ON request_tracker;
ALTER TABLE request_tracker
    DROP COLUMN request_type_text;
DROP FUNCTION fill_request_type;

-- request_tracker.service_name enum
DROP TRIGGER fill_service_name_trigger ON request_tracker;
ALTER TABLE request_tracker
    DROP COLUMN service_name_text;
DROP FUNCTION fill_service_name;
