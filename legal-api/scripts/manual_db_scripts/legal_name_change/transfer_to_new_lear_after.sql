-- ******************************************************************************************************************
-- Description:
-- Script that runs after transfer_to_new_lear.sql runs.
-- This script restores constraints removed to make data migration to the new LEAR model easier.
--
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
