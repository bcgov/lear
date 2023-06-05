-- Description:
-- Script to migrate data related to legal name model changes.
-- Summary of changes:
-- 1. Migrate SP/GP legal name(legal_entities.legal_name/legal_entities_version.legal_name) entries to
--    alternate_names/alternate_names_version tables.  The migrated entries were actually operating names and not legal
--    names.
-- 2. Remove legal_entities_version entries that were only name changes.  These should only reside in
--    alternate_names_version tables.  As a part of this update, the end transaction ids needed to be re-linked
--    to ensure that the history can still be traversed properly.
-- 3. Migrate parties/parties_version entries to legal_entities/legal_entities_version or
--    colin_entities/colin_entities_version tables.
-- 4. Update resolution/resolution_versions entries to have correct value for signing_legal_entity_id field.
-- 5. Migrate party_roles/party_roles_version to entity_roles/entity_roles_version tables.


-- disable triggers to deal with existing bad data scenarios
ALTER table legal_entities_version
    disable trigger all;
ALTER table legal_entities
    disable trigger all;
ALTER table entity_roles_version
    disable trigger all;
ALTER table entity_roles
    disable trigger all;
ALTER table addresses_version
    disable trigger all;
ALTER table addresses
    disable trigger all;

-- temp columns used to provide a way of joining newly created entries with previous party/party_roles data
ALTER TABLE legal_entities
    ADD COLUMN temp_party_id INTEGER;
ALTER TABLE colin_entities
    ADD COLUMN temp_party_id INTEGER;
ALTER TABLE entity_roles
    ADD COLUMN temp_party_role_id INTEGER;
ALTER TABLE entity_roles
    ADD COLUMN temp_party_id INTEGER;


-- Function to compare two legal_entities_version records and determine if there is a non-legal name change.
-- A predefined list of columns('legal_name', 'transaction_id', 'end_transaction_id', 'operation_type') are
-- excluded from this comparison.
CREATE OR REPLACE FUNCTION has_non_legal_name_change(identifier VARCHAR, lev_transaction_id BIGINT,
                                                     prev_lev_transaction_id BIGINT)
    RETURNS BOOLEAN
    LANGUAGE plpgsql
AS
$$
DECLARE
    rec1              json;
    rec2              json;
    columns           text;
    columns_to_ignore text[] := ARRAY ['legal_name', 'transaction_id', 'end_transaction_id', 'operation_type'];
    sql_template      VARCHAR;
BEGIN
    SELECT string_agg(quote_ident(column_name), ', ')
    INTO columns
    FROM information_schema.columns
    WHERE table_name = 'legal_entities_version'
      AND column_name != ALL (columns_to_ignore);

    sql_template :=
            'SELECT row_to_json(t) FROM (SELECT %s FROM legal_entities_version WHERE identifier = $1 and transaction_id = $2) t';
    EXECUTE format(sql_template, columns) INTO rec1 USING identifier, lev_transaction_id;
    EXECUTE format(sql_template, columns) INTO rec2 USING identifier, prev_lev_transaction_id;

    IF rec1::text IS DISTINCT FROM rec2::text THEN
        RETURN TRUE; -- Records are different
    ELSE
        RETURN FALSE; -- Records are the same
    END IF;
END ;
$$;

-- A temp table to determine which SP/GP legal entities_version records contain legal name changes and the necessary
-- query logic to determine correct end transaction ids/dates so that they can be used for
-- alternate_names/alternate_names_version entries.  This table is also used to update the existing entities_version
-- records.
CREATE TEMP TABLE temp_legal_name_changes AS
select lev.id,
       lev.identifier,
       lev.tax_id,
       prev_lev.legal_name                                as prev_legal_name,
       lev.legal_name,
       lev.operation_type,
       (CASE
            WHEN lev.legal_name != prev_lev.legal_name THEN TRUE
            WHEN lev.legal_name is not null and prev_lev.legal_name is null THEN TRUE
            ELSE FALSE
           END)                                           AS legal_name_changed,
       has_non_legal_name_change(lev.identifier, lev.transaction_id,
                                 prev_lev.transaction_id) AS non_legal_name_change,
       lev.entity_type,
       f.id                                               as filing_id,
       f.filing_type,
       f.effective_date                                   as start_date,
       (select (CASE
                    WHEN lev_next_tmp.legal_name is NULL THEN NULL
                    WHEN lev.legal_name != lev_next_tmp.legal_name THEN f_next_tmp.effective_date
                    ELSE NULL
           END) AS end_date
        from legal_entities_version lev_next_tmp
                 left join transaction t on lev_next_tmp.transaction_id = t.id
                 left join filings f_next_tmp on f_next_tmp.transaction_id = t.id
        where f_next_tmp.legal_entity_id = lev.id
          and f_next_tmp.transaction_id > lev.transaction_id
        order by f_next_tmp.transaction_id asc
        limit 1)                                          as end_date,
       lev.transaction_id,
       (select (CASE
                    WHEN lev_next_tmp.legal_name is NULL THEN NULL
                    WHEN lev.legal_name != lev_next_tmp.legal_name THEN lev_next_tmp.transaction_id
                    ELSE NULL
           END) AS legal_name_next
        from legal_entities_version lev_next_tmp
                 left join transaction t on lev_next_tmp.transaction_id = t.id
                 left join filings f_next_tmp on f_next_tmp.transaction_id = t.id
        where f_next_tmp.legal_entity_id = lev.id
          and f_next_tmp.transaction_id > lev.transaction_id
        order by f_next_tmp.transaction_id asc
        limit 1)                                          as end_transaction_id,
       prev_lev.end_transaction_id                        as prev_end_transaction_id
from legal_entities_version lev
         join transaction t on lev.transaction_id = t.id
         left join filings f on f.transaction_id = lev.transaction_id
         left join legal_entities_version prev_lev
                   on lev.transaction_id = prev_lev.end_transaction_id
where lev.entity_type in ('SP', 'GP')
order by lev.identifier, lev.transaction_id desc;


-- Insert last name change entry for SP/GPs in legal_entities_version table into alternate_names
INSERT
INTO alternate_names(legal_entity_id, identifier, name, bn15, start_date, end_date, name_type)
select id          as legal_entity_id,
       identifier,
       legal_name  as name,
       tax_id      as bn15,
       start_date,
       end_date,
       'OPERATING' as name_type
from temp_legal_name_changes lnc
         join (select max(transaction_id) as transaction_id
               from temp_legal_name_changes lnc
               where lnc.filing_id is not null
                 and lnc.legal_name_changed = True
               group by identifier) max_transaction on lnc.transaction_id = max_transaction.transaction_id
where lnc.filing_id is not null
  and lnc.legal_name_changed = True
order by lnc.transaction_id desc
;


-- Insert name change entries for SP/GPs in legal_entities_version table into alternate_names_version
INSERT
INTO alternate_names_version(id, legal_entity_id, identifier, name, bn15, start_date, end_date, name_type,
                             transaction_id, end_transaction_id, operation_type)
select an.id,
       lnc.id         as legal_entity_id,
       lnc.identifier,
       lnc.legal_name as name,
       lnc.tax_id     as bn15,
       lnc.start_date,
       lnc.end_date,
       'OPERATING'    as name_type,
       lnc.transaction_id,
       lnc.end_transaction_id,
       lnc.operation_type
from temp_legal_name_changes lnc
         join alternate_names an on an.legal_entity_id = lnc.id
where lnc.filing_id is not null
  and lnc.legal_name_changed = True
;


-- Delete legal_entities_version entries that are only name changes.  These will be represented in the
-- alternate_names_version table
delete
from legal_entities_version lev
    using temp_legal_name_changes lnc
where lev.id = lnc.id
  and lev.transaction_id = lnc.transaction_id
  and lnc.operation_type != 0
  and legal_name_changed
  and not non_legal_name_change
;


-- Create a temporary table to figure out the correct end transaction ids for the legal_entities_version table. This
-- is required as some legal_entities_version were deleted and represented in the alternate_names_version table.
-- These correct end transaction ids will used to update the legal_entities_version table.
with temp_table as (select lev.id,
                           lev.identifier,
                           lev.operation_type,
                           lev.transaction_id,
                           (select (CASE
                                        WHEN lev_next_tmp.id is NULL THEN NULL
                                        ELSE lev_next_tmp.transaction_id
                               END) AS legal_name_next
                            from legal_entities_version lev_next_tmp
                                     left join transaction t on lev_next_tmp.transaction_id = t.id
                                     left join filings f_next_tmp on f_next_tmp.transaction_id = t.id
                            where f_next_tmp.legal_entity_id = lev.id
                              and f_next_tmp.transaction_id > lev.transaction_id
                            order by f_next_tmp.transaction_id asc
                            limit 1) as end_transaction_id
                    from legal_entities_version lev
                             join transaction t on lev.transaction_id = t.id
                             left join filings f on f.transaction_id = lev.transaction_id
                    where lev.entity_type in ('SP', 'GP')
                    order by lev.identifier, lev.transaction_id desc)
update legal_entities_version lev
set end_transaction_id = tt.end_transaction_id
from temp_table tt
where lev.id = tt.id
  and lev.transaction_id = tt.transaction_id
;


-- Update SP/GP legal names to be NULL as the legal name for firms will be calculated dynamically by the API
UPDATE legal_entities_version lev
SET legal_name = NULL
where lev.entity_type in ('SP', 'GP')
  and lev.identifier like 'FM%'
;


-- Update SP/GP legal names to be NULL as the legal name for firms will be calculated dynamically by the API
UPDATE legal_entities le
SET legal_name=NULL
where le.entity_type in ('SP', 'GP')
  and le.identifier like 'FM%'
;


CREATE TEMP TABLE temp_parties_legal_name AS
select distinct pv.id                 as                                                    party_id,
                CAST(NULL AS INTEGER) as                                                    new_legal_entity_id,
                pv.party_type,
                (CASE
                     WHEN pv.party_type = 'person'
                         THEN CONCAT_WS(' ', pv.first_name, NULLIF(pv.middle_initial, ''), NULLIF(pv.last_name, ''))
                     WHEN pv.party_type = 'organization'
                         THEN pv.organization_name
                     ELSE NULL
                    END)              AS                                                    legal_name,
                pv.first_name,
                pv.middle_initial,
                pv.last_name,
                pv.title,
                pv.organization_name,
                pv.delivery_address_id,
                pv.mailing_address_id,
                pv.transaction_id,
                pv.end_transaction_id,
                pv.operation_type,
                pv.identifier,
                pv.email,
                le.id                 as                                                    matching_legal_entity_id,
                (r.id is null and pr.filing_id is null)                                     is_business_party,
                (r.id is null and pr.filing_id is null and pv.party_type = 'person')        is_business_party_person,
                (r.id is null
                    and pr.filing_id is null
                    and pv.party_type = 'organization'
                    and le.id is null
                    and
                 (pv.identifier is null or pv.identifier = '' or pv.identifier like 'FM%')) is_business_party_org_no_match,
                (r.id is null
                    and pr.filing_id is null
                    and pv.party_type = 'organization'
                    and le.id is not null)                                                  is_business_party_org_match,
                (r.id is null
                    and pr.filing_id is null
                    and le.id is null
                    and pv.party_type = 'organization'
                    and (pv.identifier is not null and pv.identifier != '' and
                         pv.identifier not like
                         'FM%'))                                                            is_business_party_colin_entity,
                (r.id is null and pr.filing_id is not null)                                 is_filing_party,
                (r.id is not null and pr.id is null)                                        is_resolution_party
from parties_version pv
         left join party_roles pr on pv.id = pr.party_id
         left join resolutions r on r.signing_party_id = pv.id
         left join legal_entities le
                   on UPPER(pv.identifier) = UPPER(le.identifier)
                       and pv.party_type = 'organization'
                       and le.entity_type in ('BEN', 'CP', 'SP', 'GP')
                       and (pv.identifier is not null and pv.identifier != '')
         join transaction t on pv.transaction_id = t.id
;

-- ************************************************************************************************
-- INSERT legal_entities records for parties
-- ************************************************************************************************

-- insert initial record for all parties except colin_entities into legal_entities table
WITH insert_parties AS (
    INSERT INTO legal_entities (entity_type, identifier, legal_name, first_name, middle_initial, last_name, title,
                                delivery_address_id,
                                mailing_address_id, email, temp_party_id)
        select tp.party_type as entity_type,
               tp.identifier,
               tp.legal_name,
               tp.first_name,
               tp.middle_initial,
               tp.last_name,
               tp.title,
               tp.delivery_address_id,
               tp.mailing_address_id,
               tp.email,
               tp.party_id   as temp_party_id
        from temp_parties_legal_name tp
                 join (select party_id, max(transaction_id) as transaction_id
                       from temp_parties_legal_name
                       where not is_business_party_colin_entity
                       group by party_id) cp
                      on cp.party_id = tp.party_id and cp.transaction_id = tp.transaction_id
        where not is_business_party_colin_entity
        RETURNING id, temp_party_id)
UPDATE temp_parties_legal_name
set new_legal_entity_id = ibp.id
from insert_parties ibp
where temp_parties_legal_name.party_id = ibp.temp_party_id
;


-- Populate signing_legal_entity_id with id from newly created legal_entity in resolutions table.
-- The signing_party_id field can now be removed from the resolutions table.
update resolutions
set signing_legal_entity_id = tp.new_legal_entity_id
from temp_parties_legal_name tp
where tp.is_resolution_party
  and tp.party_id = resolutions.signing_party_id
;


-- insert initial record for each unique business party colin entity party into colin_entities table
WITH insert_bp_colin_entity AS (
    INSERT INTO colin_entities (identifier, organization_name, delivery_address_id,
                                mailing_address_id, email, temp_party_id)
        select tp.identifier,
               tp.organization_name,
               tp.delivery_address_id,
               tp.mailing_address_id,
               tp.email,
               tp.party_id as temp_party_id
        from temp_parties_legal_name tp
                 join (select party_id, max(transaction_id) as transaction_id
                       from temp_parties_legal_name
                       where is_business_party_colin_entity
                       group by party_id) cp
                      on cp.party_id = tp.party_id and cp.transaction_id = tp.transaction_id
        where is_business_party_colin_entity
        RETURNING id, temp_party_id)
UPDATE temp_parties_legal_name
set new_legal_entity_id = ibp.id
from insert_bp_colin_entity ibp
where temp_parties_legal_name.party_id = ibp.temp_party_id
;


-- ************************************************************************************************
-- INSERT legal_entities_version records for parties
-- ************************************************************************************************

-- insert all version records for persons into legal_entities_version table
INSERT INTO legal_entities_version (id, entity_type, identifier, legal_name, first_name, middle_initial, last_name,
                                    title,
                                    delivery_address_id,
                                    mailing_address_id, email, operation_type, transaction_id, end_transaction_id)
select distinct new_legal_entity_id as id,
                party_type          as entity_type,
                identifier,
                legal_name,
                first_name,
                middle_initial,
                last_name,
                title,
                delivery_address_id,
                mailing_address_id,
                email,
                operation_type,
                transaction_id,
                end_transaction_id
from temp_parties_legal_name
where not is_business_party_colin_entity
;


-- Populate signing_legal_entity_id with corresponding legal entity id into resolutions_version table.
-- The signing_party_id field can now be removed from the resolutions_version table.
update resolutions_version
set signing_legal_entity_id = tp.new_legal_entity_id
from temp_parties_legal_name tp
where tp.is_resolution_party
  and tp.party_id = resolutions_version.signing_party_id
;


-- insert all version records for business party colin entity into colin_entities_version table
INSERT INTO colin_entities_version (id, identifier, organization_name,
                                    delivery_address_id,
                                    mailing_address_id, email, operation_type, transaction_id, end_transaction_id)
select new_legal_entity_id as id,
       identifier,
       organization_name,
       delivery_address_id,
       mailing_address_id,
       email,
       operation_type,
       transaction_id,
       end_transaction_id
from temp_parties_legal_name
where is_business_party_colin_entity
;


-- ************************************************************************************************
-- PARTY_ROLES/PARTY_ROLES_VERSION -> ENTIYTY_ROLES/ENTITY_ROLES_VERSION
-- ************************************************************************************************

CREATE TEMP TABLE temp_party_roles_legal_name AS
select id                     as party_role_id,
       CAST(NULL AS INTEGER)  as new_entity_role_id,
       role::entity_role_type as role_type,
       appointment_date,
       cessation_date,
       legal_entity_id,
       party_id,
       transaction_id,
       end_transaction_id,
       operation_type,
       filing_id
from party_roles_version
;


-- insert initial record for each unique business party person association into entity_roles table
WITH insert_parties_entity_role AS (
    INSERT INTO entity_roles (role_type, legal_entity_id, related_entity_id, appointment_date, cessation_date,
                              temp_party_role_id, temp_party_id)
        select distinct tpr.role_type,
                        tpr.legal_entity_id,
                        tp.new_legal_entity_id,
                        tpr.appointment_date,
                        tpr.cessation_date,
                        tpr.party_role_id as temp_party_role_id,
                        tp.party_id       as temp_party_id
        from temp_party_roles_legal_name tpr
                 join (select party_role_id, max(transaction_id) as transaction_id
                       from temp_party_roles_legal_name
                       group by party_role_id) cpr
                      on tpr.party_role_id = cpr.party_role_id and tpr.transaction_id = cpr.transaction_id
                 join temp_parties_legal_name tp on tpr.party_id = tp.party_id
        where not tp.is_business_party_colin_entity
          and not tp.is_resolution_party
        RETURNING id, temp_party_role_id, temp_party_id)
UPDATE temp_party_roles_legal_name
set new_entity_role_id = ibper.id
from insert_parties_entity_role ibper
where temp_party_roles_legal_name.party_role_id = ibper.temp_party_role_id
;


-- insert all version records business party persons associations into entity_roles_version table
INSERT INTO entity_roles_version (id, role_type, legal_entity_id, related_entity_id, appointment_date, cessation_date,
                                  operation_type, transaction_id, end_transaction_id)
select distinct tpr.new_entity_role_id as id,
                tpr.role_type,
                tpr.legal_entity_id,
                tp.new_legal_entity_id as related_entity_id,
                tpr.appointment_date,
                tpr.cessation_date,
                tpr.operation_type,
                tpr.transaction_id,
                tpr.end_transaction_id
from temp_party_roles_legal_name tpr
         join temp_parties_legal_name tp on tpr.party_id = tp.party_id
where not tp.is_business_party_colin_entity
  and not tp.is_resolution_party
;


-- insert initial record for colin entity association into entity_roles table
WITH insert_colin_entities_entity_role AS (
    INSERT INTO entity_roles (role_type, legal_entity_id, related_colin_entity_id, appointment_date, cessation_date,
                              temp_party_role_id, temp_party_id)
        select distinct tpr.role_type,
                        tpr.legal_entity_id,
                        tp.new_legal_entity_id,
                        tpr.appointment_date,
                        tpr.cessation_date,
                        tpr.party_role_id as temp_party_role_id,
                        tp.party_id       as temp_party_id
        from temp_party_roles_legal_name tpr
                 join (select party_role_id, max(transaction_id) as transaction_id
                       from temp_party_roles_legal_name
                       group by party_role_id) cpr
                      on tpr.party_role_id = cpr.party_role_id and tpr.transaction_id = cpr.transaction_id
                 join temp_parties_legal_name tp on tpr.party_id = tp.party_id
        where tp.is_business_party_colin_entity
          and not tp.is_resolution_party
        RETURNING id, temp_party_role_id, temp_party_id)
UPDATE temp_party_roles_legal_name
set new_entity_role_id = icer.id
from insert_colin_entities_entity_role icer
where temp_party_roles_legal_name.party_role_id = icer.temp_party_role_id
;


-- insert all version records colin entities associations into entity_roles_version table
INSERT INTO entity_roles_version (id, role_type, legal_entity_id, related_colin_entity_id, appointment_date,
                                  cessation_date,
                                  operation_type, transaction_id, end_transaction_id)
select distinct tpr.new_entity_role_id as id,
                tpr.role_type,
                tpr.legal_entity_id,
                tp.new_legal_entity_id as related_colin_entity_id,
                tpr.appointment_date,
                tpr.cessation_date,
                tpr.operation_type,
                tpr.transaction_id,
                tpr.end_transaction_id
from temp_party_roles_legal_name tpr
         join temp_parties_legal_name tp on tpr.party_id = tp.party_id
where tp.is_business_party_colin_entity
  and not tp.is_resolution_party
;


-- DROP temporarily created columns, functions and tables
DROP TABLE temp_legal_name_changes;
DROP TABLE temp_parties_legal_name;
DROP TABLE temp_party_roles_legal_name;
DROP FUNCTION has_non_legal_name_change;
ALTER TABLE legal_entities
    DROP COLUMN temp_party_id;
ALTER TABLE colin_entities
    DROP COLUMN temp_party_id;
ALTER TABLE entity_roles
    DROP COLUMN temp_party_role_id;
ALTER TABLE entity_roles
    DROP COLUMN temp_party_id;

-- re-enable triggers
ALTER table legal_entities_version
    enable trigger all;
ALTER table legal_entities
    enable trigger all;
ALTER table entity_roles_version
    enable trigger all;
ALTER table entity_roles
    enable trigger all;
ALTER table addresses_version
    enable trigger all;
ALTER table addresses
    enable trigger all;
