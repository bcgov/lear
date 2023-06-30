-- ******************************************************************************************************************
-- Description:
-- Script that runs before transfer_to_new_lear.sql runs.
-- This script disables triggers and also adds some temporary triggers/columns/functions to deal with transferring
-- enum type data.
--
-- Note: it would have been ideal to have the sql in this script in transfer_to_new_lear.sql but the tool(dbshell)
-- used to transfer data between the source(old LEAR) and target(new LEAR) database has issues with the postgres
-- enum type.  To workaround this enum issue, temporary triggers/columns/functions are used to populate the enum
-- fields properly.
-- ******************************************************************************************************************


-- DISABLE CONSTRAINTS
-- Note: Initially, the approach of disabling triggers was used to help with the data migration.  This was
-- changed as Google Cloud SQL databases do not allow disabling of triggers easily.  It was possible to disable triggers
-- on a session basis using `SET session_replication_role = 'replica';` but this did not play well with dbshell.

-- legal_entities/legal_entities_history
ALTER TABLE public.legal_entities_history
    DROP CONSTRAINT legal_entities_history_pkey;

ALTER TABLE public.legal_entities
    DROP CONSTRAINT legal_entities_delivery_address_id_fkey;
ALTER TABLE public.legal_entities
    DROP CONSTRAINT legal_entities_mailing_address_id_fkey;

ALTER TABLE public.legal_entities_history
    DROP CONSTRAINT legal_entities_history_delivery_address_id_fkey;
ALTER TABLE public.legal_entities_history
    DROP CONSTRAINT legal_entities_history_mailing_address_id_fkey;


-- addresses/addresses_history
ALTER TABLE public.addresses_history
    DROP CONSTRAINT addresses_history_pkey;

ALTER TABLE public.addresses
    DROP CONSTRAINT addresses_legal_entity_id_fkey;
ALTER TABLE public.addresses
    DROP CONSTRAINT addresses_office_id_fkey;

ALTER TABLE public.addresses_history
    DROP CONSTRAINT addresses_history_legal_entity_id_fkey;
ALTER TABLE public.addresses_history
    DROP CONSTRAINT addresses_history_office_id_fkey;


-- aliases/aliases_history
ALTER TABLE public.aliases_history
    DROP CONSTRAINT aliases_history_pkey;

ALTER TABLE public.aliases
    DROP CONSTRAINT aliases_legal_entity_id_fkey;

ALTER TABLE public.aliases_history
    DROP CONSTRAINT aliases_history_legal_entity_id_fkey;


-- offices/offices_history
ALTER TABLE public.offices_history
    DROP CONSTRAINT offices_history_pkey;

ALTER TABLE public.offices_history
    DROP CONSTRAINT offices_history_legal_entity_id_fkey;


-- parties/parties_history
ALTER TABLE public.parties_history
    DROP CONSTRAINT parties_history_pkey;

ALTER TABLE public.parties_history
    DROP CONSTRAINT parties_history_delivery_address_id_fkey;
ALTER TABLE public.parties_history
    DROP CONSTRAINT parties_history_mailing_address_id_fkey;


-- party_roles/party_roles_history
ALTER TABLE public.party_roles_history
    DROP CONSTRAINT party_roles_history_pkey;

ALTER TABLE public.party_roles_history
    DROP CONSTRAINT party_roles_history_filing_id_fkey;
ALTER TABLE public.party_roles_history
    DROP CONSTRAINT party_roles_history_legal_entity_id_fkey;
ALTER TABLE public.party_roles_history
    DROP CONSTRAINT party_roles_history_party_id_fkey;


-- share_series/share_series_history
ALTER TABLE public.share_series_history
    DROP CONSTRAINT share_series_history_pkey;

ALTER TABLE public.share_series_history
    DROP CONSTRAINT share_series_history_share_class_id_fkey;


-- entity_roles/entity_roles_history
ALTER TABLE public.entity_roles_history
    DROP CONSTRAINT entity_roles_history_pkey;

ALTER TABLE public.entity_roles
    DROP CONSTRAINT entity_roles_filing_id_fkey;
ALTER TABLE public.entity_roles
    DROP CONSTRAINT entity_roles_legal_entity_id_fkey;
ALTER TABLE public.entity_roles
    DROP CONSTRAINT entity_roles_related_entity_id_fkey;

ALTER TABLE public.entity_roles_history
    DROP CONSTRAINT entity_roles_history_filing_id_fkey;
ALTER TABLE public.entity_roles_history
    DROP CONSTRAINT entity_roles_history_legal_entity_id_fkey;
ALTER TABLE public.entity_roles_history
    DROP CONSTRAINT entity_roles_history_related_entity_id_fkey;


-- filings
ALTER TABLE public.filings
    DROP CONSTRAINT filings_parent_filing_id_fkey;
ALTER TABLE public.filings
    DROP CONSTRAINT filings_legal_entity_id_fkey;


-- Temporary columns/functions/triggers for enum workaround

ALTER TABLE public.legal_entities
    ADD COLUMN state_text text;
ALTER TABLE public.legal_entities_history
    ADD COLUMN state_text text;
ALTER TABLE public.dc_definitions
    ADD COLUMN credential_type_text text;
ALTER TABLE request_tracker
    ADD COLUMN request_type_text text;
ALTER TABLE public.request_tracker
    ADD COLUMN service_name_text text;


-- legal_entities.state & legal_entities_history.state enum
CREATE OR REPLACE FUNCTION public.fill_state() RETURNS TRIGGER AS
$$
BEGIN
    NEW.state := NEW.state_text::state;
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER fill_state_trigger
    BEFORE INSERT OR UPDATE
    ON public.legal_entities
    FOR EACH ROW
EXECUTE FUNCTION public.fill_state();

CREATE TRIGGER fill_state_history_trigger
    BEFORE INSERT OR UPDATE
    ON public.legal_entities_history
    FOR EACH ROW
EXECUTE FUNCTION public.fill_state();


-- dc_definitions.credential_type enum
CREATE OR REPLACE FUNCTION public.fill_credential_type() RETURNS TRIGGER AS
$$
BEGIN
    NEW.credential_type := NEW.credential_type_text::credentialtype;
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER fill_credential_type_trigger
    BEFORE INSERT OR UPDATE
    ON public.dc_definitions
    FOR EACH ROW
EXECUTE FUNCTION public.fill_credential_type();


-- request_tracker.request_type enum
CREATE OR REPLACE FUNCTION public.fill_request_type() RETURNS TRIGGER AS
$$
BEGIN
    NEW.request_type := NEW.request_type_text::requesttype;
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER fill_request_type_trigger
    BEFORE INSERT OR UPDATE
    ON public.request_tracker
    FOR EACH ROW
EXECUTE FUNCTION fill_request_type();


-- request_tracker.service_name enum
CREATE OR REPLACE FUNCTION public.fill_service_name() RETURNS TRIGGER AS
$$
BEGIN
    NEW.service_name := NEW.service_name_text::servicename;
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER fill_service_name_trigger
    BEFORE INSERT OR UPDATE
    ON public.request_tracker
    FOR EACH ROW
EXECUTE FUNCTION public.fill_service_name();

