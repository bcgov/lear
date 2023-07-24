-- Description:
-- Script to migrate existing data in existing LEAR(old) tables to new LEAR tables.
--
-- Notes: ensure that lear_old and lear_new connections have been configured before running this script via dbshell.

vset ignore_errors=false
vset transfer.threads=3
vset format.date=YYYY-MM-dd'T'hh:mm:ss'Z'
vset format.timestamp=YYYY-MM-dd'T'hh:mm:ss'Z'


-- *****************************************************************************************************************
-- Prep old LEAR database before transferring of data from old to new LEAR database
-- *****************************************************************************************************************

connect lear_old;

-- temp table to determine which filing_id to use for transactions that map to more than one filing which is incorrect
CREATE TABLE public.temp_multiple_filing_transactions AS
select f.id as filing_id,
       f.filing_type,
       change_filing_transaction.transaction_id
from (select t.id as transaction_id, min(f.id) as filing_id
      from public.transaction t
               join filings f on t.id = f.transaction_id
               join businesses b on f.business_id = b.id
      where t.id in (select transaction_id
                     from (select t.id as transaction_id, count(f.id) as filing_count
                           from filings f
                                    join transaction t on f.transaction_id = t.id
                           group by t.id) tblTemp
                     where filing_count > 1)
      group by t.id) change_filing_transaction
         join filings f on change_filing_transaction.filing_id = f.id
;


-- *****************************************************************************************************************
-- Transfer data from old to new LEAR database
-- *****************************************************************************************************************

connect lear_new;


-- users -> users
transfer public.users from lear_old using
select u.id,
       u.username,
       u.firstname,
       u.lastname,
       u.email,
       u.sub,
       u.iss,
       u.creation_date,
       u.middlename,
       u.idp_userid,
       u.login_source,
       COALESCE(uv.version, 1) as version
from public.users u
         left join (select id, count(transaction_id) as version
                    from users_version
                    group by id) uv on u.id = uv.id;



-- users_version -> users_history
transfer public.users_history from lear_old using
with subquery as
         (select uv.id,
                 uv.username,
                 uv.firstname,
                 uv.lastname,
                 uv.email,
                 uv.sub,
                 uv.iss,
                 uv.creation_date,
                 uv.middlename,
                 uv.idp_userid,
                 uv.login_source,
                 t.issued_at                                                                        as changed,
                 COALESCE(ROW_NUMBER() OVER (PARTITION BY uv.id ORDER BY uv.transaction_id ASC), 1) as version
          from public.users_version uv
                   left join transaction t on uv.transaction_id = t.id),
     max_versions as
         (select id, max(version) as max_version
          from subquery sq
          group by id)
select sq.*
from subquery sq
         left join max_versions mv on mv.id = sq.id
where sq.version != mv.max_version;


-- registration_bootstrap -> registration_bootstrap
transfer public.registration_bootstrap from lear_old using
SELECT identifier,
       account,
       last_modified
FROM public.registration_bootstrap;


-- filings -> filings
transfer public.filings from lear_old using
select id,
       application_date,
       approval_type,
       business_id as legal_entity_id,
       colin_only,
       completion_date,
       court_order_date,
       court_order_effect_of_order,
       court_order_file_number,
       deletion_locked,
       effective_date,
       filing_date,
       filing_json,
       filing_sub_type,
       filing_type,
       meta_data,
       notice_date,
       order_details,
       paper_only,
       parent_filing_id,
       payment_account,
       payment_completion_date,
       payment_id,
       payment_status_code,
       source,
       status,
       submitter_id,
       submitter_roles,
       tech_correction_json,
       temp_reg,
       transaction_id
from public.filings;



-- businesses -> legal_entities
CREATE CAST (varchar AS state) WITH INOUT AS IMPLICIT;

transfer public.legal_entities from lear_old using
SELECT b.id,
       b.admin_freeze,
       b.association_type,
       b.continuation_out_date,
       b.dissolution_date,
       b.fiscal_year_end_date,
       b.foreign_identifier,
       b.foreign_incorporation_date,
       b.foreign_jurisdiction,
       b.foreign_jurisdiction_region,
       b.foreign_legal_name,
       b.foreign_legal_type,
       b.founding_date,
       b.identifier,
       b.last_agm_date,
       b.last_ar_date,
       b.last_ar_reminder_year,
       b.last_ar_year,
       b.last_coa_date,
       b.last_cod_date,
       b.last_ledger_id,
       b.last_ledger_timestamp,
       b.last_modified,
       b.last_remote_ledger_id,
       b.legal_name,
       b.legal_type            as entity_type,
       b.naics_code,
       b.naics_description,
       b.naics_key,
       b.restoration_expiry_date,
       b.restriction_ind,
       b.send_ar_ind,
       b.start_date,
       b.state,
       b.state_filing_id,
       b.submitter_userid,
       b.tax_id,
       (CASE
            WHEN f.id is not null THEN f.id
            WHEN tmft.filing_id is not null THEN tmft.filing_id
            ELSE NULL
           END)                AS change_filing_id,
       COALESCE(bv.version, 1) as version
FROM public.businesses b
         left join (select id, max(transaction_id) as transaction_id, count(transaction_id) as version
                    from businesses_version bv
                    group by id) bv on b.id = bv.id
         left join public.filings f
                   on bv.transaction_id not in (select transaction_id from temp_multiple_filing_transactions) and
                      f.transaction_id = bv.transaction_id
         left join temp_multiple_filing_transactions tmft on bv.transaction_id = tmft.transaction_id
;


-- businesses_version -> legal_entities_history
transfer public.legal_entities_history from lear_old using
with subquery as
         (SELECT bv.id,
                 bv.admin_freeze,
                 bv.association_type,
                 bv.continuation_out_date,
                 bv.dissolution_date,
                 bv.fiscal_year_end_date,
                 bv.foreign_identifier,
                 bv.foreign_incorporation_date,
                 bv.foreign_jurisdiction,
                 bv.foreign_jurisdiction_region,
                 bv.foreign_legal_name,
                 bv.foreign_legal_type,
                 bv.founding_date,
                 bv.identifier,
                 bv.last_agm_date,
                 bv.last_ar_date,
                 bv.last_ar_reminder_year,
                 bv.last_ar_year,
                 bv.last_coa_date,
                 bv.last_cod_date,
                 bv.last_ledger_id,
                 bv.last_ledger_timestamp,
                 bv.last_modified,
                 bv.last_remote_ledger_id,
                 bv.legal_name,
                 bv.legal_type                                                                      as entity_type,
                 bv.naics_code,
                 bv.naics_description,
                 bv.naics_key,
                 bv.restoration_expiry_date,
                 bv.restriction_ind,
                 bv.send_ar_ind,
                 bv.start_date,
                 bv.state,
                 bv.state_filing_id,
                 bv.submitter_userid,
                 bv.tax_id,
                 (CASE
                      WHEN f.id is not null THEN f.id
                      WHEN tmft.filing_id is not null THEN tmft.filing_id
                      ELSE NULL
                     END)                                                                           AS change_filing_id,
                 t.issued_at                                                                        as changed,
                 COALESCE(ROW_NUMBER() OVER (PARTITION BY bv.id ORDER BY bv.transaction_id ASC), 1) as version
          from public.businesses_version bv
                   left join public.transaction t
                             on bv.transaction_id not in
                                (select transaction_id from temp_multiple_filing_transactions) and
                                bv.transaction_id = t.id
                   left join public.filings f on f.transaction_id = t.id
                   left join temp_multiple_filing_transactions tmft on bv.transaction_id = tmft.transaction_id),
     max_versions as
         (select id, max(version) as max_version
          from subquery sq
          group by id)
select sq.*
from subquery sq
         left join max_versions mv on mv.id = sq.id
where sq.version != mv.max_version;


-- addresses -> addresses
transfer public.addresses from lear_old using
SELECT a.id,
       a.address_type,
       a.street,
       a.street_additional,
       a.city,
       a.region,
       a.country,
       a.postal_code,
       a.delivery_instructions,
       a.business_id           as legal_entity_id,
       a.office_id,
       (CASE
            WHEN f.id is not null THEN f.id
            WHEN tmft.filing_id is not null THEN tmft.filing_id
            ELSE NULL
           END)                AS change_filing_id,
       COALESCE(av.version, 0) as version
FROM public.addresses a
         left join (select id, max(transaction_id) as transaction_id, count(transaction_id) as version
                    from public.addresses_version
                    group by id) av on a.id = av.id
         left join public.filings f
                   on av.transaction_id not in (select transaction_id from temp_multiple_filing_transactions) and
                      f.transaction_id = av.transaction_id
         left join temp_multiple_filing_transactions tmft on av.transaction_id = tmft.transaction_id
;


-- addresses_version -> addresses_history
transfer public.addresses_history from lear_old using
with subquery as
         (SELECT av.id,
                 av.address_type,
                 av.street,
                 av.street_additional,
                 av.city,
                 av.region,
                 av.country,
                 av.postal_code,
                 av.delivery_instructions,
                 av.business_id                                                                     as legal_entity_id,
                 av.office_id,
                 (CASE
                      WHEN f.id is not null THEN f.id
                      WHEN tmft.filing_id is not null THEN tmft.filing_id
                      ELSE NULL
                     END)                                                                           AS change_filing_id,
                 t.issued_at                                                                        as changed,
                 COALESCE(ROW_NUMBER() OVER (PARTITION BY av.id ORDER BY av.transaction_id ASC), 1) as version
          from public.addresses_version av
                   left join public.transaction t
                             on av.transaction_id not in
                                (select transaction_id from temp_multiple_filing_transactions) and
                                av.transaction_id = t.id
                   left join public.filings f on f.transaction_id = t.id
                   left join temp_multiple_filing_transactions tmft on av.transaction_id = tmft.transaction_id),
     max_versions as
         (select id, max(version) as max_version
          from subquery sq
          group by id)
select sq.*
from subquery sq
         left join max_versions mv on mv.id = sq.id
where sq.version != mv.max_version;


-- aliases -> aliases
transfer public.aliases from lear_old using
SELECT a.id,
       a.alias,
       a.type,
       a.business_id           as legal_entity_id,
       f.id                    as change_filing_id,
       COALESCE(av.version, 0) as version
FROM public.aliases a
         left join (select id, max(transaction_id) as transaction_id, count(transaction_id) as version
                    from public.aliases_version
                    group by id) av on a.id = av.id
         left join public.filings f on f.transaction_id = av.transaction_id;


-- aliases_version -> aliases_history
transfer public.aliases_history from lear_old using
with subquery as
         (SELECT av.id,
                 av.alias,
                 av.type,
                 av.business_id                                                                     as legal_entity_id,
                 f.id                                                                               as change_filing_id,
                 t.issued_at                                                                        as changed,
                 COALESCE(ROW_NUMBER() OVER (PARTITION BY av.id ORDER BY av.transaction_id ASC), 1) as version
          from public.aliases_version av
                   left join public.transaction t on av.transaction_id = t.id
                   left join public.filings f on f.transaction_id = t.id),
     max_versions as
         (select id, max(version) as max_version
          from subquery sq
          group by id)
select sq.*
from subquery sq
         left join max_versions mv on mv.id = sq.id
where sq.version != mv.max_version;


-- colin_event_ids -> colin_event_ids
transfer public.colin_event_ids from lear_old using
SELECT colin_event_id,
       filing_id
FROM public.colin_event_ids;


-- colin_last_update -> colin_last_update
transfer public.colin_last_update from lear_old using
SELECT id,
       last_update,
       last_event_id
FROM public.colin_last_update;


-- comments -> comments
transfer public.comments from lear_old using
SELECT id,
       comment,
       timestamp,
       business_id as legal_entity_id,
       staff_id,
       filing_id
FROM public.comments;


-- dc_connections -> dc_connections
transfer public.dc_connections from lear_old using
SELECT id,
       connection_id,
       invitation_url,
       is_active,
       connection_state,
       business_id as legal_entity_id
FROM public.dc_connections;


-- dc_definitions -> dc_definitions
CREATE CAST (varchar AS credentialtype) WITH INOUT AS IMPLICIT;

transfer public.dc_definitions from lear_old using
SELECT id,
       credential_type,
       schema_id,
       schema_name,
       schema_version,
       credential_definition_id,
       is_deleted
FROM public.dc_definitions;


-- dc_issued_credentials -> dc_issued_credentials
transfer public.dc_issued_credentials from lear_old using
SELECT id,
       dc_definition_id,
       dc_connection_id,
       credential_exchange_id,
       credential_id,
       is_issued,
       date_of_issue,
       is_revoked
FROM public.dc_issued_credentials;


-- documents -> documents
transfer public.documents from lear_old using
SELECT d.id,
       d.type,
       d.file_key,
       d.business_id           as legal_entity_id,
       d.filing_id,
       COALESCE(dv.version, 1) as version
FROM public.documents d
         left join (select id, count(transaction_id) as version
                    from public.documents_version
                    group by id) dv on d.id = dv.id;


-- documents_version -> documents_history
transfer public.documents_history from lear_old using
with subquery as
         (SELECT dv.id,
                 dv.type,
                 dv.file_key,
                 dv.business_id                                                                     as legal_entity_id,
                 dv.filing_id,
                 t.issued_at                                                                        as changed,
                 COALESCE(ROW_NUMBER() OVER (PARTITION BY dv.id ORDER BY dv.transaction_id ASC), 1) as version
          from public.documents_version dv
                   left join public.transaction t on dv.transaction_id = t.id),
     max_versions as
         (select id, max(version) as max_version
          from subquery sq
          group by id)
select sq.*
from subquery sq
         left join max_versions mv on mv.id = sq.id
where sq.version != mv.max_version;


-- offices -> offices
transfer public.offices from lear_old using
SELECT distinct o.id,
                o.office_type,
                o.deactivated_date,
                o.business_id           as legal_entity_id,
                (CASE
                     WHEN f.id is not null THEN f.id
                     WHEN tmft.filing_id is not null THEN tmft.filing_id
                     ELSE NULL
                    END)                AS change_filing_id,

                COALESCE(ov.version, 1) as version
FROM public.offices o
         left join (select id, max(transaction_id) as transaction_id, count(transaction_id) as version
                    from public.offices_version
                    group by id) ov on o.id = ov.id
         left join public.filings f
                   on ov.transaction_id not in (select transaction_id from temp_multiple_filing_transactions) and
                      f.transaction_id = ov.transaction_id
         left join temp_multiple_filing_transactions tmft on ov.transaction_id = tmft.transaction_id;


-- offices_version -> offices_history
transfer public.offices_history from lear_old using
with subquery as
         (SELECT ov.id,
                 ov.office_type,
                 (CASE
                      WHEN ov.operation_type = 2 THEN f.effective_date
                      ELSE NULL
                     END)                                                                           as deactivated_date,
                 ov.business_id                                                                     as legal_entity_id,
                 (CASE
                      WHEN f.id is not null THEN f.id
                      WHEN tmft.filing_id is not null THEN tmft.filing_id
                      ELSE NULL
                     END)                                                                           AS change_filing_id,
                 t.issued_at                                                                        as changed,
                 COALESCE(ROW_NUMBER() OVER (PARTITION BY ov.id ORDER BY ov.transaction_id ASC), 1) as version
          from public.offices_version ov
                   left join public.transaction t
                             on ov.transaction_id not in
                                (select transaction_id from temp_multiple_filing_transactions) and
                                ov.transaction_id = t.id
                   left join public.filings f on f.transaction_id = t.id
                   left join temp_multiple_filing_transactions tmft on ov.transaction_id = tmft.transaction_id),
     max_versions as
         (select id, max(version) as max_version
          from subquery sq
          group by id)
select sq.*
from subquery sq
         left join max_versions mv on mv.id = sq.id
where sq.deactivated_date is not null
   or sq.version != mv.max_version;


-- parties -> parties
transfer public.parties from lear_old using
SELECT p.id,
       p.party_type,
       p.first_name,
       p.middle_initial,
       p.last_name,
       p.title,
       p.organization_name,
       p.delivery_address_id,
       p.mailing_address_id,
       p.identifier,
       p.email,
       (CASE
            WHEN f.id is not null THEN f.id
            WHEN tmft.filing_id is not null THEN tmft.filing_id
            ELSE NULL
           END)                AS change_filing_id,
       COALESCE(pv.version, 1) as version
FROM public.parties p
         left join (select id, max(transaction_id) as transaction_id, count(transaction_id) as version
                    from public.parties_version
                    group by id) pv on p.id = pv.id
         left join public.filings f
                   on pv.transaction_id not in (select transaction_id from temp_multiple_filing_transactions) and
                      f.transaction_id = pv.transaction_id
         left join temp_multiple_filing_transactions tmft on pv.transaction_id = tmft.transaction_id;


-- parties_version -> parties_history
transfer public.parties_history from lear_old using
with subquery as
         (SELECT pv.id,
                 pv.party_type,
                 pv.first_name,
                 pv.middle_initial,
                 pv.last_name,
                 pv.title,
                 pv.organization_name,
                 pv.delivery_address_id,
                 pv.mailing_address_id,
                 pv.identifier,
                 pv.email,
                 (CASE
                      WHEN f.id is not null THEN f.id
                      WHEN tmft.filing_id is not null THEN tmft.filing_id
                      ELSE NULL
                     END)                                                                       AS change_filing_id,
                 t.issued_at                                                                    as changed,
                 COALESCE(ROW_NUMBER() OVER (PARTITION BY pv.id ORDER BY pv.transaction_id), 1) as version
          from public.parties_version pv
                   left join public.transaction t
                             on pv.transaction_id not in
                                (select transaction_id from temp_multiple_filing_transactions) and
                                pv.transaction_id = t.id
                   left join public.filings f on f.transaction_id = t.id
                   left join temp_multiple_filing_transactions tmft on pv.transaction_id = tmft.transaction_id),
     max_versions as
         (select id, max(version) as max_version
          from subquery sq
          group by id)
select sq.*
from subquery sq
         left join max_versions mv on mv.id = sq.id
where sq.version != mv.max_version
;


-- party_roles -> party_roles
transfer public.party_roles from lear_old using
SELECT pr.id,
       pr.role,
       pr.appointment_date,
       pr.cessation_date,
       pr.business_id           as legal_entity_id,
       pr.party_id,
       pr.filing_id,
       (CASE
            WHEN f.id is not null THEN f.id
            WHEN tmft.filing_id is not null THEN tmft.filing_id
            ELSE NULL
           END)                 AS change_filing_id,
       COALESCE(prv.version, 1) as version
FROM public.party_roles pr
         left join (select id, max(transaction_id) as transaction_id, count(transaction_id) as version
                    from public.party_roles_version
                    group by id) prv on pr.id = prv.id
         left join public.filings f
                   on prv.transaction_id not in (select transaction_id from temp_multiple_filing_transactions) and
                      f.transaction_id = prv.transaction_id
         left join temp_multiple_filing_transactions tmft on prv.transaction_id = tmft.transaction_id
;


-- party_roles_version -> party_roles_history
transfer public.party_roles_history from lear_old using
with subquery as
         (SELECT prv.id,
                 prv.role,
                 prv.appointment_date,
                 prv.cessation_date,
                 prv.business_id                                                                      as legal_entity_id,
                 prv.party_id,
                 prv.filing_id,
                 (CASE
                      WHEN f.id is not null THEN f.id
                      WHEN tmft.filing_id is not null THEN tmft.filing_id
                      ELSE NULL
                     END)                                                                             AS change_filing_id,
                 t.issued_at                                                                          as changed,
                 COALESCE(ROW_NUMBER() OVER (PARTITION BY prv.id ORDER BY prv.transaction_id ASC), 1) as version
          from public.party_roles_version prv
                   left join public.transaction t
                             on prv.transaction_id not in
                                (select transaction_id from temp_multiple_filing_transactions) and
                                prv.transaction_id = t.id
                   left join public.filings f on f.transaction_id = t.id
                   left join temp_multiple_filing_transactions tmft on prv.transaction_id = tmft.transaction_id),
     max_versions as
         (select id, max(version) as max_version
          from subquery sq
          group by id)
select sq.*
from subquery sq
         left join max_versions mv on mv.id = sq.id
where sq.version != mv.max_version;


-- request_tracker -> request_tracker
CREATE CAST (varchar AS requesttype) WITH INOUT AS IMPLICIT;
CREATE CAST (varchar AS servicename) WITH INOUT AS IMPLICIT;

transfer public.request_tracker from lear_old using
SELECT id,
       request_type,
       is_processed,
       request_object,
       response_object,
       retry_number,
       service_name,
       business_id  as legal_entity_id,
       creation_date,
       last_modified,
       filing_id,
       is_admin,
       message_id
FROM public.request_tracker;


-- resolutions -> resolutions
transfer public.resolutions from lear_old using
SELECT r.id,
       r.resolution_date,
       r.type,
       r.business_id           as legal_entity_id,
       r.resolution,
       r.signing_date,
       r.signing_party_id,
       r.sub_type,
       f.id                    as change_filing_id,
       COALESCE(rv.version, 1) as version
FROM public.resolutions r
         left join (select id, max(transaction_id) as transaction_id, count(transaction_id) as version
                    from public.resolutions_version
                    group by id) rv on r.id = rv.id
         left join public.filings f on f.transaction_id = rv.transaction_id;



-- resolutions_version -> resolutions_history
transfer public.resolutions_history from lear_old using
with subquery as
         (SELECT rv.id,
                 rv.resolution_date,
                 rv.type,
                 rv.business_id                                                                     as legal_entity_id,
                 rv.resolution,
                 rv.signing_date,
                 rv.signing_party_id,
                 rv.sub_type,
                 f.id                                                                               as change_filing_id,
                 t.issued_at                                                                        as changed,
                 COALESCE(ROW_NUMBER() OVER (PARTITION BY rv.id ORDER BY rv.transaction_id ASC), 1) as version
          from public.resolutions_version rv
                   left join public.transaction t on rv.transaction_id = t.id
                   left join public.filings f on f.transaction_id = t.id),
     max_versions as
         (select id, max(version) as max_version
          from subquery sq
          group by id)
select sq.*
from subquery sq
         left join max_versions mv on mv.id = sq.id
where sq.version != mv.max_version;



-- share_classes -> share_classes
transfer public.share_classes from lear_old using
SELECT sc.id,
       sc.name,
       sc.priority,
       sc.max_share_flag,
       sc.max_shares,
       sc.par_value_flag,
       sc.par_value,
       sc.currency,
       sc.special_rights_flag,
       sc.business_id           as legal_entity_id,
       f.id                     as change_filing_id,
       COALESCE(scv.version, 1) as version
FROM public.share_classes sc
         left join (select id, max(transaction_id) as transaction_id, count(transaction_id) as version
                    from public.share_classes_version
                    group by id) scv on sc.id = scv.id
         left join public.filings f on f.transaction_id = scv.transaction_id;


-- share_classes_version -> share_classes_history
transfer public.share_classes_history from lear_old using
with subquery as
         (SELECT scv.id,
                 scv.name,
                 scv.priority,
                 scv.max_share_flag,
                 scv.max_shares,
                 scv.par_value_flag,
                 scv.par_value,
                 scv.currency,
                 scv.special_rights_flag,
                 scv.business_id                                                                      as legal_entity_id,
                 f.id                                                                                 as change_filing_id,
                 t.issued_at                                                                          as changed,
                 COALESCE(ROW_NUMBER() OVER (PARTITION BY scv.id ORDER BY scv.transaction_id ASC), 1) as version
          from public.share_classes_version scv
                   left join public.transaction t on scv.transaction_id = t.id
                   left join public.filings f on f.transaction_id = t.id),
     max_versions as
         (select id, max(version) as max_version
          from subquery sq
          group by id)
select sq.*
from subquery sq
         left join max_versions mv on mv.id = sq.id
where sq.version != mv.max_version;


-- share_series -> share_series
transfer public.share_series from lear_old using
SELECT ss.id,
       ss.name,
       ss.priority,
       ss.max_share_flag,
       ss.max_shares,
       ss.special_rights_flag,
       ss.share_class_id,
       f.id                     as change_filing_id,
       COALESCE(ssv.version, 1) as version
FROM public.share_series ss
         left join (select id, max(transaction_id) as transaction_id, count(transaction_id) as version
                    from public.share_series_version ssv
                    group by id) ssv on ss.id = ssv.id
         left join public.filings f on f.transaction_id = ssv.transaction_id;


-- share_series_version -> share_series_history
transfer public.share_series_history from lear_old using
with subquery as
         (SELECT ssv.id,
                 ssv.name,
                 ssv.priority,
                 ssv.max_share_flag,
                 ssv.max_shares,
                 ssv.special_rights_flag,
                 ssv.share_class_id,
                 f.id                                                                                 as change_filing_id,
                 t.issued_at                                                                          as changed,
                 COALESCE(ROW_NUMBER() OVER (PARTITION BY ssv.id ORDER BY ssv.transaction_id ASC), 0) as version
          from public.share_series_version ssv
                   left join public.transaction t on ssv.transaction_id = t.id
                   left join public.filings f on f.transaction_id = t.id),
     max_versions as
         (select id, max(version) as max_version
          from subquery sq
          group by id)
select sq.*
from subquery sq
         left join max_versions mv on mv.id = sq.id
where sq.version != mv.max_version;


-- consent_continuation_outs -> consent_continuation_outs
transfer public.consent_continuation_outs from lear_old using
SELECT cco.id,
       cco.foreign_jurisdiction,
       cco.foreign_jurisdiction_region,
       cco.expiry_date,
       cco.filing_id,
       cco.business_id as legal_entity_id
FROM public.consent_continuation_outs cco;


-- sent_to_gazette -> sent_to_gazette
transfer public.sent_to_gazette from lear_old using
SELECT stg.filing_id,
       stg.identifier,
       stg.sent_to_gazette_date
FROM public.sent_to_gazette stg;



-- ensure sequence numbers are updated so collisions with future data does not happen
SELECT setval('users_id_seq', (select coalesce(max(id) + 1, 1) FROM public.users));
SELECT setval('legal_entities_id_seq', (select coalesce(max(id) + 1, 1) FROM public.legal_entities));
SELECT setval('entity_roles_id_seq', (select coalesce(max(id) + 1, 1) FROM public.entity_roles));
SELECT setval('colin_entities_id_seq', (select coalesce(max(id) + 1, 1) FROM public.colin_entities));
SELECT setval('legal_entity_identifier_coop', (select MAX(CAST(substring(identifier, '(1[0-9]{6})') AS INTEGER)) + 1
                                               from legal_entities
                                               where entity_type = 'CP'));
SELECT setval('legal_entity_identifier_sp_gp', (select MAX(CAST(substring(identifier, '(1[0-9]{6})') AS INTEGER)) + 1
                                                from legal_entities
                                                where entity_type in ('SP', 'GP')));
SELECT setval('filings_id_seq', (select coalesce(max(id) + 1, 1) FROM public.filings));
SELECT setval('addresses_id_seq', (select coalesce(max(id) + 1, 1) FROM public.addresses));
SELECT setval('aliases_id_seq', (select coalesce(max(id) + 1, 1) FROM public.aliases));
SELECT setval('colin_event_ids_colin_event_id_seq', (SELECT coalesce(max(colin_event_id) + 1, 1) FROM public.colin_event_ids));
SELECT setval('colin_last_update_id_seq', (select coalesce(max(id) + 1, 1) FROM public.colin_last_update));
SELECT setval('comments_id_seq', (select coalesce(max(id) + 1, 1) FROM public.comments));
SELECT setval('dc_definitions_id_seq', (select coalesce(max(id) + 1, 1) FROM public.dc_definitions));
SELECT setval('dc_connections_id_seq', (select coalesce(max(id) + 1, 1) FROM public.dc_connections));
SELECT setval('dc_issued_credentials_id_seq', (select coalesce(max(id) + 1, 1) FROM public.dc_issued_credentials));
SELECT setval('documents_id_seq', (select coalesce(max(id) + 1, 1) FROM public.documents));
SELECT setval('offices_id_seq', (select coalesce(max(id) + 1, 1) FROM public.offices));
SELECT setval('parties_id_seq', (select coalesce(max(id) + 1, 1) FROM public.parties));
SELECT setval('party_roles_id_seq', (select coalesce(max(id) + 1, 1) FROM public.party_roles));
SELECT setval('request_tracker_id_seq', (select coalesce(max(id) + 1, 1) FROM public.request_tracker));
SELECT setval('resolutions_id_seq', (select coalesce(max(id) + 1, 1) FROM public.resolutions));
SELECT setval('share_classes_id_seq', (select coalesce(max(id) + 1, 1) FROM public.share_classes));
SELECT setval('share_series_id_seq', (select coalesce(max(id) + 1, 1) FROM public.share_series));
SELECT setval('entity_roles_id_seq', (select coalesce(max(id) + 1, 1) FROM public.share_series));
SELECT setval('legal_entities_id_seq', (select coalesce(max(id) + 1, 1) FROM public.legal_entities));
SELECT setval('colin_entities_id_seq', (select coalesce(max(id) + 1, 1) FROM public.colin_entities));
SELECT setval('alternate_names_id_seq', (select coalesce(max(id) + 1, 1) FROM public.alternate_names));
SELECT setval('users_id_seq', (select coalesce(max(id) + 1, 1) FROM public.users));
SELECT setval('consent_continuation_outs_id_seq', (select coalesce(max(id) + 1, 1) FROM public.consent_continuation_outs));

DROP CAST (varchar AS state);
DROP CAST (varchar AS credentialtype);
DROP CAST (varchar AS requesttype);
DROP CAST (varchar AS servicename);


-- *****************************************************************************************************************
-- Cleanup of any necessary artifacts/states created as a part of data transfer
-- *****************************************************************************************************************

connect lear_old;

DROP TABLE public.temp_multiple_filing_transactions;

