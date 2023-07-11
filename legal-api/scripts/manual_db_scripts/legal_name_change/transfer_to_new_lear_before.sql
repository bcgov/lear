-- ******************************************************************************************************************
-- Description:
-- Script that runs before transfer_to_new_lear.sql runs.
-- This script removes constraints to make data loading to new LEAR model easier.
--
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
