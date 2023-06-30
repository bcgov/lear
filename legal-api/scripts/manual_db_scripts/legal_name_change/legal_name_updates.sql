-- Description:
-- Script to migrate data related to legal name model changes.
-- Summary of changes:
-- 1. Migrate SP/GP legal name(legal_entities.legal_name/legal_entities_history.legal_name) entries to
--    alternate_names/alternate_names_history tables.  The migrated entries were actually operating names and not legal
--    names.
-- 2. Remove legal_entities_history entries that were only name changes.  These should only reside in
--    alternate_names_history tables.  As a part of this update, the end transaction ids needed to be re-linked
--    to ensure that the history can still be traversed properly.
-- 3. Migrate parties/parties_history entries to legal_entities/legal_entities_history or
--    colin_entities/colin_entities_history tables.
-- 4. Update resolution/resolution_historys entries to have correct value for signing_legal_entity_id field.
-- 5. Migrate party_roles/party_roles_history to entity_roles/entity_roles_history tables.
-- 6. Update party ids in filing json to use newly created legal_entities_ids for filing types(COD, correction, AR,
--    changeOfRegistration and conversion) that contain references to party ids.


-- temp columns used to provide a way of joining newly created entries with previous party/party_roles data
ALTER TABLE legal_entities
    ADD COLUMN temp_party_id INTEGER;
ALTER TABLE colin_entities
    ADD COLUMN temp_party_id INTEGER;
ALTER TABLE entity_roles
    ADD COLUMN temp_party_role_id INTEGER;
ALTER TABLE entity_roles
    ADD COLUMN temp_party_id INTEGER;


-- Function to compare two legal_entities_history records and determine if there is a non-legal name change.
-- A predefined list of columns('legal_name', 'version', 'change_filing_id', 'changed') are
-- excluded from this comparison.
CREATE OR REPLACE FUNCTION has_non_legal_name_change(identifier VARCHAR, leh_version INT,
                                                     prev_leh_version INT)
    RETURNS BOOLEAN
    LANGUAGE plpgsql
AS
$$
DECLARE
    rec1              json;
    rec2              json;
    columns           text;
    columns_to_ignore text[] := ARRAY ['legal_name', 'version', 'change_filing_id', 'changed'];
    sql_template      VARCHAR;
BEGIN
    SELECT string_agg(quote_ident(column_name), ', ')
    INTO columns
    FROM information_schema.columns
    WHERE table_name = 'legal_entities_history'
      AND column_name != ALL (columns_to_ignore);

    sql_template :=
            'SELECT row_to_json(t) FROM (SELECT %s FROM legal_entities_history WHERE identifier = $1 and version = $2) t';
    EXECUTE format(sql_template, columns) INTO rec1 USING identifier, leh_version;
    EXECUTE format(sql_template, columns) INTO rec2 USING identifier, prev_leh_version;

    IF rec1::text IS DISTINCT FROM rec2::text THEN
        RETURN TRUE; -- Records are different
    ELSE
        RETURN FALSE; -- Records are the same
    END IF;
END ;
$$;

-- A temp table to determine which SP/GP legal entities_history records contain legal name changes and the necessary
-- query logic to determine correct end transaction ids/dates so that they can be used for
-- alternate_names/alternate_names_history entries.  This table is also used to update the existing entities_history
-- records.
CREATE TEMP TABLE temp_legal_name_changes AS
select leh.id,
       leh.identifier,
       leh.tax_id,
       prev_leh.legal_name                              as prev_legal_name,
       leh.legal_name,
       (CASE
            WHEN leh.legal_name != prev_leh.legal_name THEN TRUE
            WHEN leh.legal_name is not null and prev_leh.legal_name is null THEN TRUE
            ELSE FALSE
           END)                                         AS legal_name_changed,
       has_non_legal_name_change(leh.identifier, leh.version,
                                 prev_leh.version)      AS non_legal_name_change,
       leh.entity_type,
       f.id                                             as filing_id,
       f.filing_type,
       f.effective_date                                 as start_date,
       (select (CASE
                    WHEN leh_next_tmp.legal_name is NULL THEN NULL
                    WHEN leh.legal_name != leh_next_tmp.legal_name THEN f_next_tmp.effective_date
                    ELSE NULL
           END) AS end_date
        from legal_entities_history leh_next_tmp
                 left join filings f_next_tmp on f_next_tmp.id = leh_next_tmp.change_filing_id
        where f_next_tmp.legal_entity_id = leh.id
          and leh_next_tmp.version = (leh.version + 1)) as end_date,
       leh.version
from legal_entities_history leh
         left join filings f on f.id = leh.change_filing_id
         left join legal_entities_history prev_leh
                   on leh.id = prev_leh.id and prev_leh.version = leh.version - 1
where leh.entity_type in ('SP', 'GP')
order by leh.identifier, leh.version desc;


-- Insert last name change entry for SP/GPs in legal_entities_history table into alternate_names
INSERT
INTO alternate_names(legal_entity_id, identifier, name, bn15, start_date, end_date, name_type, change_filing_id,
                     version)
select lnc.id                  as legal_entity_id,
       identifier,
       legal_name              as name,
       tax_id                  as bn15,
       start_date,
       end_date,
       'OPERATING'             as name_type,
       lnc.filing_id           as change_filing_id,
       max_version.new_version as version
from temp_legal_name_changes lnc
         join (select id,
                      max(version)       as version_match,
                      count(version) - 1 as new_version
               from temp_legal_name_changes lnc
               where lnc.filing_id is not null
                 and lnc.legal_name_changed = True
               group by id) max_version on lnc.id = max_version.id and lnc.version = max_version.version_match
where lnc.filing_id is not null
  and lnc.legal_name_changed = True
order by lnc.version desc
;


-- Insert name change entries for SP/GPs in legal_entities_history table into alternate_names_history
INSERT
INTO alternate_names_history(id, legal_entity_id, identifier, name, bn15, start_date, end_date, name_type,
                             version, change_filing_id, changed)
select an.id,
       lnc.id                                                              as legal_entity_id,
       lnc.identifier,
       lnc.legal_name                                                      as name,
       lnc.tax_id                                                          as bn15,
       lnc.start_date,
       lnc.end_date,
       'OPERATING'                                                         as name_type,
       ROW_NUMBER() OVER (PARTITION BY an.id ORDER BY lnc.version ASC) - 1 as version,
       lnc.filing_id                                                       as change_filing_id,
       lnc.start_date                                                      as changed
from temp_legal_name_changes lnc
         join alternate_names an on an.legal_entity_id = lnc.id
where lnc.filing_id is not null
  and lnc.legal_name_changed = True
;


-- Delete legal_entities_history entries that are only name changes.  These will be represented in the
-- alternate_names_history table
delete
from legal_entities_history leh
    using temp_legal_name_changes lnc
where leh.id = lnc.id
  and leh.version = lnc.version
  and leh.version != 0
  and legal_name_changed
  and not non_legal_name_change
;


-- Update version numbers to ensure correct version numbers are in place for each legal_entities_history entries.
-- This is required as some legal_entities_history were deleted and moved to the alternate_names_history table.
-- In the cases where legal_entities_history entries were moved, the version numbers will having missing version numbers.
with temp_legal_entities_history AS
         (select id,
                 identifier,
                 version                                                      as old_version,
                 ROW_NUMBER() OVER (PARTITION BY id ORDER BY version ASC) - 1 as new_version
          from legal_entities_history
          where entity_type in ('SP', 'GP')
          order by id, version desc)
update legal_entities_history
set version = tleh.new_version
from temp_legal_entities_history tleh
where legal_entities_history.id = tleh.id
  and legal_entities_history.version = tleh.old_version
;

-- Update version numbers to ensure correct version numbers are in place for each legal_entities entries.
-- This is required as some legal_entities_history were deleted and moved to the alternate_names_history table.
-- In the cases where legal_entities_history entries were moved, the corresponding legal_entities version number
-- may be incorrect.
update legal_entities le
set version = tempLeh.maxVersion
from (select id, max(version) as maxVersion
      from legal_entities_history
      group by id) as tempLeh
where le.id = tempLeh.id
;


-- Update SP/GP legal names to be NULL as the legal name for firms will be calculated dynamically by the API
UPDATE legal_entities_history leh
SET legal_name = NULL
where leh.entity_type in ('SP', 'GP')
  and leh.identifier like 'FM%'
;


-- Update SP/GP legal names to be NULL as the legal name for firms will be calculated dynamically by the API
UPDATE legal_entities le
SET legal_name=NULL
where le.entity_type in ('SP', 'GP')
  and le.identifier like 'FM%'
;


CREATE TEMP TABLE temp_parties_legal_name AS
select distinct ph.id                 as                                                    party_id,
                CAST(NULL AS INTEGER) as                                                    new_legal_entity_id,
                ph.party_type,
                (CASE
                     WHEN ph.party_type = 'person'
                         THEN CONCAT_WS(' ', ph.first_name, NULLIF(ph.middle_initial, ''), NULLIF(ph.last_name, ''))
                     WHEN ph.party_type = 'organization'
                         THEN ph.organization_name
                     ELSE NULL
                    END)              AS                                                    legal_name,
                ph.first_name,
                ph.middle_initial,
                ph.last_name,
                ph.title,
                ph.organization_name,
                ph.delivery_address_id,
                ph.mailing_address_id,
                ph.version,
                ph.changed,
                ph.change_filing_id,
                f.effective_date      as                                                    change_filing_effective_date,
                ph.identifier,
                ph.email,
                le.id                 as                                                    matching_legal_entity_id,
                (r.id is null and pr.filing_id is null)                                     is_business_party,
                (r.id is null and pr.filing_id is null and ph.party_type = 'person')        is_business_party_person,
                (r.id is null
                    and pr.filing_id is null
                    and ph.party_type = 'organization'
                    and le.id is null
                    and
                 (ph.identifier is null or ph.identifier = '' or ph.identifier like 'FM%')) is_business_party_org_no_match,
                (r.id is null
                    and pr.filing_id is null
                    and ph.party_type = 'organization'
                    and le.id is not null)                                                  is_business_party_org_match,
                (r.id is null
                    and pr.filing_id is null
                    and le.id is null
                    and ph.party_type = 'organization'
                    and (ph.identifier is not null and ph.identifier != '' and
                         ph.identifier not like
                         'FM%'))                                                            is_business_party_colin_entity,
                (r.id is null and pr.filing_id is not null)                                 is_filing_party,
                (r.id is not null and pr.id is null)                                        is_resolution_party
from parties_history ph
         left join party_roles pr on ph.id = pr.party_id
         left join resolutions r on r.signing_party_id = ph.id
         left join legal_entities le
                   on UPPER(ph.identifier) = UPPER(le.identifier)
                       and ph.party_type = 'organization'
                       and le.entity_type in ('BEN', 'CP', 'SP', 'GP')
                       and (ph.identifier is not null and ph.identifier != '')
         left join filings f on f.id = ph.change_filing_id
;


-- ************************************************************************************************
-- INSERT legal_entities records for parties
-- ************************************************************************************************

-- insert initial record for all parties except colin_entities into legal_entities table
WITH insert_parties AS (
    INSERT INTO legal_entities (entity_type, identifier, legal_name, first_name, middle_initial, last_name, title,
                                delivery_address_id,
                                mailing_address_id, email, temp_party_id, change_filing_id, version)
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
               tp.party_id   as temp_party_id,
               tp.change_filing_id,
               cp.version
        from temp_parties_legal_name tp
                 join (select party_id, max(version) as version
                       from temp_parties_legal_name
                       where not is_business_party_colin_entity
                       group by party_id) cp
                      on cp.party_id = tp.party_id and cp.version = tp.version
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
                                mailing_address_id, email, temp_party_id, change_filing_id, version)
        select tp.identifier,
               tp.organization_name,
               tp.delivery_address_id,
               tp.mailing_address_id,
               tp.email,
               tp.party_id as temp_party_id,
               tp.change_filing_id,
               cp.version
        from temp_parties_legal_name tp
                 join (select party_id, max(version) as version
                       from temp_parties_legal_name
                       where is_business_party_colin_entity
                       group by party_id) cp
                      on cp.party_id = tp.party_id and cp.version = tp.version
        where is_business_party_colin_entity
        RETURNING id, temp_party_id)
UPDATE temp_parties_legal_name
set new_legal_entity_id = ibp.id
from insert_bp_colin_entity ibp
where temp_parties_legal_name.party_id = ibp.temp_party_id
;


-- ************************************************************************************************
-- INSERT legal_entities_history records for parties
-- ************************************************************************************************

-- insert all version records for persons into legal_entities_history table
INSERT INTO legal_entities_history (id, entity_type, identifier, legal_name, first_name, middle_initial, last_name,
                                    title, delivery_address_id, mailing_address_id, email, version, change_filing_id,
                                    changed)
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
                version,
                change_filing_id,
                changed
from temp_parties_legal_name
where not is_business_party_colin_entity
;


-- Populate signing_legal_entity_id with corresponding legal entity id into resolutions_history table.
-- The signing_party_id field can now be removed from the resolutions_history table.
update resolutions_history
set signing_legal_entity_id = tp.new_legal_entity_id
from temp_parties_legal_name tp
where tp.is_resolution_party
  and tp.party_id = resolutions_history.signing_party_id
;


-- insert all version records for business party colin entity into colin_entities_history table
INSERT INTO colin_entities_history (id, identifier, organization_name,
                                    delivery_address_id,
                                    mailing_address_id, email, change_filing_id, changed, version)
select new_legal_entity_id as id,
       identifier,
       organization_name,
       delivery_address_id,
       mailing_address_id,
       email,
       change_filing_id,
       changed,
       version
from temp_parties_legal_name
where is_business_party_colin_entity
;


-- ************************************************************************************************
-- PARTY_ROLES/PARTY_ROLES_history -> ENTIYTY_ROLES/ENTITY_ROLES_history
-- ************************************************************************************************

CREATE TEMP TABLE temp_party_roles_legal_name AS
select id                    as party_role_id,
       CAST(NULL AS INTEGER) as new_entity_role_id,
       role::roletypes       as role_type,
       appointment_date,
       cessation_date,
       legal_entity_id,
       party_id,
       filing_id,
       change_filing_id,
       changed,
       version
from party_roles_history
;


-- insert initial record for each unique business party person association into entity_roles table
WITH insert_parties_entity_role AS (
    INSERT INTO entity_roles (role_type, legal_entity_id, related_entity_id, appointment_date, cessation_date,
                              temp_party_role_id, temp_party_id, filing_id, change_filing_id, version)
        select distinct tpr.role_type,
                        tpr.legal_entity_id,
                        tp.new_legal_entity_id,
                        tpr.appointment_date,
                        tpr.cessation_date,
                        tpr.party_role_id as temp_party_role_id,
                        tp.party_id       as temp_party_id,
                        tpr.filing_id,
                        tpr.change_filing_id,
                        tpr.version
        from temp_party_roles_legal_name tpr
                 join (select party_role_id, max(version) as version
                       from temp_party_roles_legal_name
                       group by party_role_id) cpr
                      on tpr.party_role_id = cpr.party_role_id and tpr.version = cpr.version
                 join temp_parties_legal_name tp on tpr.party_id = tp.party_id
        where not tp.is_business_party_colin_entity
          and not tp.is_resolution_party
        RETURNING id, temp_party_role_id, temp_party_id)
UPDATE temp_party_roles_legal_name
set new_entity_role_id = ibper.id
from insert_parties_entity_role ibper
where temp_party_roles_legal_name.party_role_id = ibper.temp_party_role_id
;

-- insert all version records business party persons associations into entity_roles_history table
INSERT INTO entity_roles_history (id, role_type, legal_entity_id, related_entity_id, appointment_date, cessation_date,
                                  filing_id, change_filing_id, changed, version)
select distinct tpr.new_entity_role_id as id,
                tpr.role_type,
                tpr.legal_entity_id,
                tp.new_legal_entity_id as related_entity_id,
                tpr.appointment_date,
                tpr.cessation_date,
                tpr.filing_id,
                tpr.change_filing_id,
                tpr.changed,
                tpr.version
from temp_party_roles_legal_name tpr
         join temp_parties_legal_name tp on tpr.party_id = tp.party_id
where not tp.is_business_party_colin_entity
  and not tp.is_resolution_party
;


-- insert initial record for colin entity association into entity_roles table
WITH insert_colin_entities_entity_role AS (
    INSERT INTO entity_roles (role_type, legal_entity_id, related_colin_entity_id, appointment_date, cessation_date,
                              temp_party_role_id, temp_party_id, change_filing_id, version)
        select distinct tpr.role_type,
                        tpr.legal_entity_id,
                        tp.new_legal_entity_id,
                        tpr.appointment_date,
                        tpr.cessation_date,
                        tpr.party_role_id as temp_party_role_id,
                        tp.party_id       as temp_party_id,
                        tpr.change_filing_id,
                        tpr.version
        from temp_party_roles_legal_name tpr
                 join (select party_role_id, max(version) as version
                       from temp_party_roles_legal_name
                       group by party_role_id) cpr
                      on tpr.party_role_id = cpr.party_role_id and tpr.version = cpr.version
                 join temp_parties_legal_name tp on tpr.party_id = tp.party_id
        where tp.is_business_party_colin_entity
          and not tp.is_resolution_party
        RETURNING id, temp_party_role_id, temp_party_id)
UPDATE temp_party_roles_legal_name
set new_entity_role_id = icer.id
from insert_colin_entities_entity_role icer
where temp_party_roles_legal_name.party_role_id = icer.temp_party_role_id
;


-- insert all version records colin entities associations into entity_roles_history table
INSERT INTO entity_roles_history (id, role_type, legal_entity_id, related_colin_entity_id, appointment_date,
                                  cessation_date,
                                  filing_id, change_filing_id, changed, version)
select distinct tpr.new_entity_role_id as id,
                tpr.role_type,
                tpr.legal_entity_id,
                tp.new_legal_entity_id as related_colin_entity_id,
                tpr.appointment_date,
                tpr.cessation_date,
                tpr.filing_id,
                tpr.change_filing_id,
                tpr.changed,
                tpr.version
from temp_party_roles_legal_name tpr
         join temp_parties_legal_name tp on tpr.party_id = tp.party_id
where tp.is_business_party_colin_entity
  and not tp.is_resolution_party
;

-- ************************************************************************************************
-- Update filing json to replace party ids with newly created legal entity ids for COD, correction,
-- AR,changeOfRegistration and conversion filing types.
-- ************************************************************************************************

-- Function to update party ids with new legal entity ids for an existing filing json value.
-- path_to_array accepts the json path to the list item property that represents the party entries
-- for a given filing type.
CREATE OR REPLACE FUNCTION update_filing_json_party_ids(path_to_array TEXT[])
    RETURNS VOID AS
$$
BEGIN
    with new_ids as (SELECT distinct f.id                                            as filing_id,
                                     CAST(elements -> 'officer' ->> 'id' as integer) AS old_party_id,
                                     tpln.new_legal_entity_id                        as new_party_id
                     FROM filings f,
                          jsonb_array_elements(f.filing_json #> path_to_array) as elements
                              left join temp_parties_legal_name tpln
                                        on elements.value -> 'officer' ->> 'id' SIMILAR TO '[0-9]+'
                                            and tpln.party_id = CAST(elements -> 'officer' ->> 'id' as integer)
                     where 1 = 1
                       and elements.value -> 'officer' ->> 'id' is not null
                       and elements.value -> 'officer' ? 'id'
                       and elements.value -> 'officer' ->> 'id' SIMILAR TO '[0-9]+'),
         updated_filing_json as (SELECT f.id                                                                           AS filing_id,
                                        jsonb_set(f.filing_json, path_to_array,
                                                  (SELECT jsonb_agg(CASE
                                                                        WHEN elem.value ->
                                                                             'officer' ->>
                                                                             'id' SIMILAR TO
                                                                             '[0-9]+' and
                                                                             CAST(elem -> 'officer' ->> 'id' as integer) IN
                                                                             (SELECT old_party_id
                                                                              FROM new_ids tni
                                                                              WHERE filing_id = tni.filing_id)
                                                                            THEN
                                                                            jsonb_set(elem, '{officer,id}',
                                                                                      to_jsonb(
                                                                                              (SELECT new_party_id
                                                                                               FROM new_ids tni
                                                                                               WHERE filing_id = f.id
                                                                                                 AND elem.value -> 'officer' ->> 'id' SIMILAR TO '[0-9]+'
                                                                                                 AND old_party_id = CAST(elem -> 'officer' ->> 'id' as integer))::text))
                                                                        ELSE elem
                                                      END)
                                                   FROM jsonb_array_elements(f.filing_json #> path_to_array) AS elem)) AS new_filing_json
                                 FROM filings f
                                 WHERE f.id IN (SELECT filing_id FROM new_ids))
    update filings f
    set filing_json = updated_filing_json.new_filing_json
    from updated_filing_json
    where f.id = updated_filing_json.filing_id;
END;
$$ LANGUAGE plpgsql;


-- Replace filing json party ids with correct legal entity ids for relevant filing types
SELECT update_filing_json_party_ids('{filing,changeOfDirectors,directors}');
SELECT update_filing_json_party_ids('{filing,correction,parties}');
SELECT update_filing_json_party_ids('{filing,annualReport,directors}');
SELECT update_filing_json_party_ids('{filing,changeOfRegistration,parties}');
SELECT update_filing_json_party_ids('{filing,conversion,parties}');


-- DROP temporarily created columns, functions and tables
DROP TABLE temp_legal_name_changes;
DROP TABLE temp_parties_legal_name;
DROP TABLE temp_party_roles_legal_name;
DROP FUNCTION has_non_legal_name_change;
DROP FUNCTION update_filing_json_party_ids;
ALTER TABLE legal_entities
    DROP COLUMN temp_party_id;
ALTER TABLE colin_entities
    DROP COLUMN temp_party_id;
ALTER TABLE entity_roles
    DROP COLUMN temp_party_role_id;
ALTER TABLE entity_roles
    DROP COLUMN temp_party_id;


VACUUM FULL;
