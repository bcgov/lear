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


-- RESTORE CONSTRAINTS

-- legal_entities/legal_entities_history
ALTER TABLE public.legal_entities_history
    ADD CONSTRAINT legal_entities_history_pkey PRIMARY KEY (id, version);

ALTER TABLE public.legal_entities
    ADD CONSTRAINT legal_entities_delivery_address_id_fkey FOREIGN KEY (delivery_address_id) REFERENCES public.addresses (id);
ALTER TABLE public.legal_entities
    ADD CONSTRAINT legal_entities_mailing_address_id_fkey FOREIGN KEY (mailing_address_id) REFERENCES public.addresses (id);

ALTER TABLE public.legal_entities_history
    ADD CONSTRAINT legal_entities_history_delivery_address_id_fkey FOREIGN KEY (delivery_address_id) REFERENCES public.addresses (id);
ALTER TABLE public.legal_entities_history
    ADD CONSTRAINT legal_entities_history_mailing_address_id_fkey FOREIGN KEY (mailing_address_id) REFERENCES public.addresses (id);


-- addresses/addresses_history
ALTER TABLE public.addresses_history
    ADD CONSTRAINT addresses_history_pkey PRIMARY KEY (id, version);

ALTER TABLE public.addresses
    ADD CONSTRAINT addresses_legal_entity_id_fkey FOREIGN KEY (legal_entity_id) REFERENCES public.legal_entities (id);
ALTER TABLE public.addresses
    ADD CONSTRAINT addresses_office_id_fkey FOREIGN KEY (office_id) REFERENCES public.offices (id) ON DELETE CASCADE;

ALTER TABLE public.addresses_history
    ADD CONSTRAINT addresses_history_legal_entity_id_fkey FOREIGN KEY (legal_entity_id) REFERENCES public.legal_entities (id);
ALTER TABLE public.addresses_history
    ADD CONSTRAINT addresses_history_office_id_fkey FOREIGN KEY (office_id) REFERENCES public.offices (id) ON DELETE CASCADE;


-- aliases/aliases_history
ALTER TABLE public.aliases_history
    ADD CONSTRAINT aliases_history_pkey PRIMARY KEY (id, version);

ALTER TABLE public.aliases
    ADD CONSTRAINT aliases_legal_entity_id_fkey FOREIGN KEY (legal_entity_id) REFERENCES public.legal_entities (id);

ALTER TABLE public.aliases_history
    ADD CONSTRAINT aliases_history_legal_entity_id_fkey FOREIGN KEY (legal_entity_id) REFERENCES public.legal_entities (id);


-- offices/offices_history
ALTER TABLE public.offices_history
    ADD CONSTRAINT offices_history_pkey PRIMARY KEY (id, version);

ALTER TABLE public.offices_history
    ADD CONSTRAINT offices_history_legal_entity_id_fkey FOREIGN KEY (legal_entity_id) REFERENCES public.legal_entities (id);


-- parties/parties_history
ALTER TABLE public.parties_history
    ADD CONSTRAINT parties_history_pkey PRIMARY KEY (id, version);

ALTER TABLE public.parties_history
    ADD CONSTRAINT parties_history_delivery_address_id_fkey FOREIGN KEY (delivery_address_id) REFERENCES public.addresses (id);
ALTER TABLE public.parties_history
    ADD CONSTRAINT parties_history_mailing_address_id_fkey FOREIGN KEY (mailing_address_id) REFERENCES public.addresses (id);


-- party_roles/party_roles_history
ALTER TABLE public.party_roles_history
    ADD CONSTRAINT party_roles_history_pkey PRIMARY KEY (id, version);

ALTER TABLE public.party_roles_history
    ADD CONSTRAINT party_roles_history_filing_id_fkey FOREIGN KEY (filing_id) REFERENCES public.filings (id);
ALTER TABLE public.party_roles_history
    ADD CONSTRAINT party_roles_history_legal_entity_id_fkey FOREIGN KEY (legal_entity_id) REFERENCES public.legal_entities (id);
ALTER TABLE public.party_roles_history
    ADD CONSTRAINT party_roles_history_party_id_fkey FOREIGN KEY (party_id) REFERENCES public.parties (id);


-- share_series/share_series_history
ALTER TABLE public.share_series_history
    ADD CONSTRAINT share_series_history_pkey PRIMARY KEY (id, version);

ALTER TABLE public.share_series_history
    ADD CONSTRAINT share_series_history_share_class_id_fkey FOREIGN KEY (share_class_id) REFERENCES public.share_classes (id);


-- entity_roles/entity_roles_history
ALTER TABLE public.entity_roles_history
    ADD CONSTRAINT entity_roles_history_pkey PRIMARY KEY (id, version);

ALTER TABLE public.entity_roles
    ADD CONSTRAINT entity_roles_related_colin_entity_id_fkey FOREIGN KEY (related_colin_entity_id) REFERENCES public.colin_entities (id);
ALTER TABLE public.entity_roles
    ADD CONSTRAINT entity_roles_filing_id_fkey FOREIGN KEY (filing_id) REFERENCES public.filings (id);
ALTER TABLE public.entity_roles
    ADD CONSTRAINT entity_roles_legal_entity_id_fkey FOREIGN KEY (legal_entity_id) REFERENCES public.legal_entities (id);
ALTER TABLE public.entity_roles
    ADD CONSTRAINT entity_roles_related_entity_id_fkey FOREIGN KEY (related_entity_id) REFERENCES public.legal_entities (id);

ALTER TABLE public.entity_roles_history
    ADD CONSTRAINT entity_roles_history_filing_id_fkey FOREIGN KEY (filing_id) REFERENCES public.filings (id);
ALTER TABLE public.entity_roles_history
    ADD CONSTRAINT entity_roles_history_legal_entity_id_fkey FOREIGN KEY (legal_entity_id) REFERENCES public.legal_entities (id);
ALTER TABLE public.entity_roles_history
    ADD CONSTRAINT entity_roles_history_related_entity_id_fkey FOREIGN KEY (related_entity_id) REFERENCES public.legal_entities (id);


-- filings
ALTER TABLE public.filings
    ADD CONSTRAINT filings_parent_filing_id_fkey FOREIGN KEY (parent_filing_id) REFERENCES public.filings (id);
ALTER TABLE public.filings
    ADD CONSTRAINT filings_legal_entity_id_fkey FOREIGN KEY (legal_entity_id) REFERENCES public.legal_entities (id);


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
