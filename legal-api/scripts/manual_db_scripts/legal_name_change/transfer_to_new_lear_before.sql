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

-- Disable triggers
ALTER TABLE public.users
    DISABLE TRIGGER ALL;
ALTER TABLE public.users_history
    DISABLE TRIGGER ALL;
ALTER TABLE public.dc_definitions
    DISABLE TRIGGER ALL;
ALTER TABLE public.legal_entities
    DISABLE TRIGGER ALL;
ALTER TABLE public.legal_entities_history
    DISABLE TRIGGER ALL;
ALTER TABLE public.filings
    DISABLE TRIGGER ALL;
ALTER TABLE public.addresses
    DISABLE TRIGGER ALL;
ALTER TABLE public.addresses_history
    DISABLE TRIGGER ALL;
ALTER TABLE public.aliases
    DISABLE TRIGGER ALL;
ALTER TABLE public.aliases_history
    DISABLE TRIGGER ALL;
ALTER TABLE public.colin_event_ids
    DISABLE TRIGGER ALL;
ALTER TABLE public.colin_last_update
    DISABLE TRIGGER ALL;
ALTER TABLE public.comments
    DISABLE TRIGGER ALL;
ALTER TABLE public.dc_connections
    DISABLE TRIGGER ALL;
ALTER TABLE public.dc_definitions
    DISABLE TRIGGER ALL;
ALTER TABLE public.dc_issued_credentials
    DISABLE TRIGGER ALL;
ALTER TABLE public.documents
    DISABLE TRIGGER ALL;
ALTER TABLE public.documents_history
    DISABLE TRIGGER ALL;
ALTER TABLE public.offices
    DISABLE TRIGGER ALL;
ALTER TABLE public.offices_history
    DISABLE TRIGGER ALL;
ALTER TABLE public.parties
    DISABLE TRIGGER ALL;
ALTER TABLE public.parties_history
    DISABLE TRIGGER ALL;
ALTER TABLE public.party_roles
    DISABLE TRIGGER ALL;
ALTER TABLE public.party_roles_history
    DISABLE TRIGGER ALL;
ALTER TABLE public.registration_bootstrap
    DISABLE TRIGGER ALL;
ALTER TABLE public.request_tracker
    DISABLE TRIGGER ALL;
ALTER TABLE public.resolutions
    DISABLE TRIGGER ALL;
ALTER TABLE public.resolutions_history
    DISABLE TRIGGER ALL;
ALTER TABLE public.share_classes
    DISABLE TRIGGER ALL;
ALTER TABLE public.share_classes_history
    DISABLE TRIGGER ALL;
ALTER TABLE public.share_series
    DISABLE TRIGGER ALL;
ALTER TABLE public.share_series_history
    DISABLE TRIGGER ALL;
ALTER TABLE public.consent_continuation_outs
    DISABLE TRIGGER ALL;
ALTER TABLE public.sent_to_gazette
    DISABLE TRIGGER ALL;


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

