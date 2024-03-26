-- Description:
-- Script to migrate data related to legal name model changes.
-- Summary of changes:
-- 1. Migrate SP/GP legal name(legal_entities.legal_name/legal_entities_history.legal_name) entries to
--    alternate_names/alternate_names_history tables.  The migrated entries were actually dba names and not legal
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

-- Function to replace an existing key name with a new key name
CREATE OR REPLACE FUNCTION rename_jsonb_key(json_data JSONB, old_key TEXT, new_key TEXT)
    RETURNS JSONB AS
$$
DECLARE
    result JSONB;
    key    TEXT;
BEGIN
    IF json_data ? old_key THEN
        result := json_data #- ARRAY [old_key];
        result := jsonb_set(result, ARRAY [new_key], json_data -> old_key);
    ELSE
        result := json_data;
    END IF;

    IF jsonb_typeof(json_data) = 'object' THEN
        FOR key IN
            SELECT * FROM jsonb_object_keys(json_data)
            LOOP
                IF jsonb_typeof(json_data -> key) = 'object' THEN
                    result := jsonb_set(result, ARRAY [key], rename_jsonb_key(json_data -> key, old_key, new_key));
                ELSIF jsonb_typeof(json_data -> key) = 'array' THEN
                    result := jsonb_set(result, ARRAY [key],
                                        (SELECT jsonb_agg(rename_jsonb_key(value, old_key, new_key))
                                         FROM jsonb_array_elements(json_data -> key)));
                END IF;
            END LOOP;
    END IF;

    RETURN result;
END;
$$
    LANGUAGE plpgsql;



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
CREATE TABLE temp_legal_name_changes AS
select le.id,
       le.identifier,
       le.tax_id,
       prev_leh.legal_name                         as prev_legal_name,
       le.legal_name,
       (CASE
            WHEN le.legal_name != prev_leh.legal_name THEN TRUE
            WHEN le.legal_name is not null and prev_leh.legal_name is null THEN TRUE
            ELSE FALSE
           END)                                    AS legal_name_changed,
       has_non_legal_name_change(le.identifier, le.version,
                                 prev_leh.version) AS non_legal_name_change,
       le.entity_type,
       f.id                                        as filing_id,
       f.filing_type,
       f.effective_date                            as start_date,
       null                                        as end_date,
       null                                        as next_filing_id,
       le.version,
       le.naics_key,
       le.naics_code,
       le.naics_description,
       le.start_date                               as business_start_date,
       le.dissolution_date,
       le.admin_freeze,
       le.state,
       le.state_filing_id,
       le.last_modified
from legal_entities le
         left join filings f on f.id = le.change_filing_id
         left join (select id, max(version) as max_version from legal_entities_history group by id) prev_leh_version
                   on le.id = prev_leh_version.id
         left join legal_entities_history prev_leh
                   on prev_leh.id = prev_leh_version.id and prev_leh.version = prev_leh_version.max_version
where le.entity_type in ('SP', 'GP')
UNION
select leh.id,
       leh.identifier,
       leh.tax_id,
       prev_leh.legal_name                         as prev_legal_name,
       leh.legal_name,
       (CASE
            WHEN leh.legal_name != prev_leh.legal_name THEN TRUE
            WHEN leh.legal_name is not null and prev_leh.legal_name is null THEN TRUE
            ELSE FALSE
           END)                                    AS legal_name_changed,
       has_non_legal_name_change(leh.identifier, leh.version,
                                 prev_leh.version) AS non_legal_name_change,
       leh.entity_type,
       f.id                                        as filing_id,
       f.filing_type,
       f.effective_date                            as start_date,
       next_leh.end_date,
       next_leh.next_filing_id,
       leh.version,
       leh.naics_key,
       leh.naics_code,
       leh.naics_description,
       leh.start_date                              as business_start_date,
       leh.dissolution_date,
       leh.admin_freeze,
       leh.state,
       leh.state_filing_id,
       leh.last_modified
from legal_entities_history leh
         left join filings f on f.id = leh.change_filing_id
         left join legal_entities_history prev_leh
                   on leh.id = prev_leh.id and prev_leh.version = leh.version - 1
         left join legal_entities le on leh.id = le.id
         left join lateral (select (CASE
                                        WHEN tmp_next_le.legal_name is NULL THEN NULL
                                        WHEN leh.legal_name != tmp_next_le.legal_name THEN tmp_next_le.effective_date
                                        ELSE NULL
    END)                                                 AS end_date,
                                   tmp_next_le.filing_id AS next_filing_id
                            from (select leh_next_tmp.legal_name,
                                         f_next_tmp.effective_date,
                                         f_next_tmp.id as filing_id
                                  from legal_entities_history leh_next_tmp
                                           left join filings f_next_tmp
                                                     on f_next_tmp.id = leh_next_tmp.change_filing_id
                                  where f_next_tmp.legal_entity_id = leh.id
                                    and leh_next_tmp.version = (leh.version + 1)
                                  UNION
                                  select le_next_tmp.legal_name, f_next_tmp.effective_date, f_next_tmp.id as filing_id
                                  from legal_entities le_next_tmp
                                           left join filings f_next_tmp on f_next_tmp.id = le_next_tmp.change_filing_id
                                  where f_next_tmp.legal_entity_id = leh.id
                                    and le_next_tmp.version = (leh.version + 1)) tmp_next_le

                            where tmp_next_le.legal_name is not null) next_leh
                   on true
where leh.entity_type in ('SP', 'GP')
;


-- Insert last name change entry for SP/GPs in legal_entities_history table into alternate_names
INSERT
INTO alternate_names(legal_entity_id, identifier, name, entity_type, bn15, start_date, end_date, name_type,
                     naics_key, naics_code, naics_description, business_start_date, dissolution_date,
                     admin_freeze, state, state_filing_id, last_modified, change_filing_id, version)
select lnc.id                as legal_entity_id,
       identifier,
       legal_name            as name,
       entity_type           as entity_type,
       tax_id                as bn15,
       start_date,
       end_date,
       'DBA'::nametype as name_type,
       CASE WHEN lnc.entity_type = 'SP' THEN naics_key ELSE NULL END,
       CASE WHEN lnc.entity_type = 'SP' THEN naics_code ELSE NULL END,
       CASE WHEN lnc.entity_type = 'SP' THEN naics_description ELSE NULL END,
       CASE WHEN lnc.entity_type = 'SP' THEN business_start_date ELSE NULL END,
       CASE WHEN lnc.entity_type = 'SP' THEN dissolution_date ELSE NULL END,
       CASE WHEN lnc.entity_type = 'SP' THEN admin_freeze ELSE NULL END,
       CASE WHEN lnc.entity_type = 'SP' THEN state ELSE NULL END,
       CASE WHEN lnc.entity_type = 'SP' THEN state_filing_id ELSE NULL END,
       CASE WHEN lnc.entity_type = 'SP' THEN last_modified ELSE NULL END,
       lnc.filing_id         as change_filing_id,
       1                     as version
from temp_legal_name_changes lnc
         join (select id,
                      max(version)   as version_match,
                      count(version) as new_version
               from temp_legal_name_changes lnc
               where lnc.filing_id is not null
                 and lnc.legal_name_changed = True
               group by id) max_version on lnc.id = max_version.id and lnc.version = max_version.version_match
where lnc.filing_id is not null
  and lnc.legal_name_changed = True
order by lnc.version desc
;


-- Insert name change entries for SP/GPs in legal_entities_history table into alternate_names_history
WITH id_values AS (SELECT nextval('alternate_names_id_seq') as an_seq_id, lnc.*
                   FROM temp_legal_name_changes lnc
                            join alternate_names an on an.legal_entity_id = lnc.id
                   WHERE lnc.filing_id is not null
                     AND lnc.legal_name_changed = True
                     and lnc.filing_id != an.change_filing_id)
INSERT
INTO alternate_names_history(id, legal_entity_id, identifier, name, entity_type, bn15, start_date, end_date, name_type,
                             naics_key, naics_code, naics_description, business_start_date, dissolution_date,
                             admin_freeze, state, state_filing_id, last_modified, version, change_filing_id, changed)
SELECT id_values.an_seq_id   as id,
       id_values.id          as legal_entity_id,
       id_values.identifier,
       id_values.legal_name  as name,
       id_values.entity_type as entity_type,
       id_values.tax_id      as bn15,
       id_values.start_date,
       NULL                  as end_date,
       'DBA'::nametype as name_type,
       CASE WHEN id_values.entity_type = 'SP' THEN naics_key ELSE NULL END,
       CASE WHEN id_values.entity_type = 'SP' THEN naics_code ELSE NULL END,
       CASE WHEN id_values.entity_type = 'SP' THEN naics_description ELSE NULL END,
       CASE WHEN id_values.entity_type = 'SP' THEN business_start_date ELSE NULL END,
       CASE WHEN id_values.entity_type = 'SP' THEN dissolution_date ELSE NULL END,
       CASE WHEN id_values.entity_type = 'SP' THEN admin_freeze ELSE NULL END,
       CASE WHEN id_values.entity_type = 'SP' THEN state ELSE NULL END,
       CASE WHEN id_values.entity_type = 'SP' THEN state_filing_id ELSE NULL END,
       CASE WHEN id_values.entity_type = 'SP' THEN last_modified ELSE NULL END,
       1                     as version,
       id_values.filing_id   as change_filing_id,
       id_values.start_date  as changed
FROM id_values

UNION ALL

SELECT id_values.an_seq_id      as id,
       id_values.id             as legal_entity_id,
       id_values.identifier,
       id_values.legal_name     as name,
       id_values.entity_type    as entity_type,
       id_values.tax_id         as bn15,
       id_values.start_date,
       id_values.end_date       as end_date,
       'DBA'::nametype    as name_type,
       CASE WHEN id_values.entity_type = 'SP' THEN naics_key ELSE NULL END,
       CASE WHEN id_values.entity_type = 'SP' THEN naics_code ELSE NULL END,
       CASE WHEN id_values.entity_type = 'SP' THEN naics_description ELSE NULL END,
       CASE WHEN id_values.entity_type = 'SP' THEN business_start_date ELSE NULL END,
       CASE WHEN id_values.entity_type = 'SP' THEN dissolution_date ELSE NULL END,
       CASE WHEN id_values.entity_type = 'SP' THEN admin_freeze ELSE NULL END,
       CASE WHEN id_values.entity_type = 'SP' THEN state ELSE NULL END,
       CASE WHEN id_values.entity_type = 'SP' THEN state_filing_id ELSE NULL END,
       CASE WHEN id_values.entity_type = 'SP' THEN last_modified ELSE NULL END,
       2                        as version,
       id_values.next_filing_id as change_filing_id,
       id_values.end_date       as changed
FROM id_values;


-- Delete legal_entities_history entries that are only name changes.  These will be represented in the
-- alternate_names_history table
delete
from legal_entities_history leh
    using temp_legal_name_changes lnc
where leh.id = lnc.id
  and leh.version = lnc.version
  and leh.version != 1
  and legal_name_changed
  and not non_legal_name_change
;


-- Update version numbers to ensure correct version numbers are in place for each legal_entities_history entries.
-- This is required as some legal_entities_history were deleted and moved to the alternate_names_history table.
-- In the cases where legal_entities_history entries were moved, the version numbers will having missing version numbers.
with temp_legal_entities_history AS
         (select id,
                 identifier,
                 version                                                  as old_version,
                 ROW_NUMBER() OVER (PARTITION BY id ORDER BY version ASC) as new_version
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
from (select le.id,
             CASE
                 when max_leh_version.id is null then 1
                 else max_leh_version.maxVersion + 1
                 end as maxVersion
      from legal_entities le
               left join (select id, max(version) as maxVersion
                          from legal_entities_history
                          group by id) max_leh_version on le.id = max_leh_version.id) as tempLeh
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


CREATE TABLE temp_parties_legal_name AS
select distinct ph.id                                                                        as party_id,
                (CASE
                     WHEN pr.role = 'proprietor' and ph.party_type = 'person'
                         THEN pr.legal_entity_id
                     ELSE CAST(NULL AS INTEGER)
                    END)                                                                     AS new_legal_entity_id,
                ph.party_type,
                (CASE
                     WHEN ph.party_type = 'person'
                         THEN NULL
                     WHEN ph.party_type = 'organization'
                         THEN ph.organization_name
                     ELSE NULL
                    END)                                                                     AS legal_name,
                ph.first_name,
                ph.middle_initial,
                ph.last_name,
                ph.title,
                ph.organization_name,
                COALESCE((pr.role = 'proprietor' and ph.party_type = 'person'), FALSE)       as is_proprietor_person,
                COALESCE((pr.role = 'proprietor' and ph.party_type = 'organization'), FALSE) as is_proprietor_org,
                ph.delivery_address_id,
                ph.mailing_address_id,
                ph.changed,
                ph.change_filing_id,
                f.effective_date                                                             as change_filing_effective_date,
                ph.identifier,
                ph.email,
                le.id                                                                        as matching_legal_entity_id,
                (r.id is null and pr.filing_id is null)                                         is_business_party,
                (r.id is null and pr.filing_id is null and ph.party_type = 'person')            is_business_party_person,
                (r.id is null
                    and pr.filing_id is null
                    and ph.party_type = 'organization'
                    and le.id is null
                    and (ph.identifier is null or ph.identifier = '' or ph.identifier like 'FM%')
                    )                                                                           is_business_party_org_no_match,
                (r.id is null
                    and pr.filing_id is null
                    and ph.party_type = 'organization'
                    and
                 le.id is not null)                                                             is_business_party_org_match,
                (r.id is null
                    and pr.filing_id is null
                    and le.id is null
                    and ph.party_type =
                        'organization')                                                         is_business_party_colin_entity,
                (r.id is null and pr.filing_id is not null)                                     is_filing_party,
                (r.id is not null and pr.id is null)                                            is_resolution_party,
                ph.version,
                cp.version                                                                   as max_version
from parties_history ph
         left join party_roles pr on ph.id = pr.party_id
         left join resolutions r on r.signing_party_id = ph.id
         left join legal_entities le
                   on UPPER(ph.identifier) = UPPER(le.identifier)
                       and ph.party_type = 'organization'
                       and le.entity_type in ('BEN', 'CP', 'SP', 'GP')
                       and (ph.identifier is not null and ph.identifier != '')
         left join filings f on f.id = ph.change_filing_id
         join parties cp on cp.id = ph.id
UNION
select distinct p.id                                                                        as party_id,
                (CASE
                     WHEN pr.role = 'proprietor' and p.party_type = 'person'
                         THEN pr.legal_entity_id
                     ELSE CAST(NULL AS INTEGER)
                    END)                                                                    AS new_legal_entity_id,
                p.party_type,
                (CASE
                     WHEN p.party_type = 'person'
                         THEN NULL
                     WHEN p.party_type = 'organization'
                         THEN p.organization_name
                     ELSE NULL
                    END)                                                                    AS legal_name,
                p.first_name,
                p.middle_initial,
                p.last_name,
                p.title,
                p.organization_name,
                COALESCE((pr.role = 'proprietor' and p.party_type = 'person'), FALSE)       as is_proprietor_person,
                COALESCE((pr.role = 'proprietor' and p.party_type = 'organization'), FALSE) as is_proprietor_org,
                p.delivery_address_id,
                p.mailing_address_id,
                f.effective_date                                                            as changed,
                p.change_filing_id,
                f.effective_date                                                            as change_filing_effective_date,
                p.identifier,
                p.email,
                le.id                                                                       as matching_legal_entity_id,
                (r.id is null and pr.filing_id is null)                                        is_business_party,
                (r.id is null and pr.filing_id is null and p.party_type = 'person')            is_business_party_person,
                (r.id is null
                    and pr.filing_id is null
                    and p.party_type = 'organization'
                    and le.id is null
                    and (p.identifier is null or p.identifier = '' or p.identifier like 'FM%')
                    )                                                                          is_business_party_org_no_match,
                (r.id is null
                    and pr.filing_id is null
                    and p.party_type = 'organization'
                    and
                 le.id is not null)                                                            is_business_party_org_match,
                (r.id is null
                    and pr.filing_id is null
                    and le.id is null
                    and p.party_type =
                        'organization')                                                        is_business_party_colin_entity,
                (r.id is null and pr.filing_id is not null)                                    is_filing_party,
                (r.id is not null and pr.id is null)                                           is_resolution_party,
                p.version,
                p.version                                                                   as max_version
from parties p
         left join party_roles pr on p.id = pr.party_id
         left join resolutions r on r.signing_party_id = p.id
         left join legal_entities le
                   on UPPER(p.identifier) = UPPER(le.identifier)
                       and p.party_type = 'organization'
                       and le.entity_type in ('BEN', 'CP', 'SP', 'GP')
                       and (p.identifier is not null and p.identifier != '')
         left join filings f on f.id = p.change_filing_id
;


-- ************************************************************************************************
-- INSERT legal_entities records for parties
-- ************************************************************************************************

-- insert initial record for all parties except colin_entities into legal_entities table
WITH insert_parties AS (
    INSERT INTO legal_entities (entity_type, identifier, legal_name, first_name, middle_initial, last_name, title,
                                delivery_address_id,
                                mailing_address_id, email, temp_party_id, change_filing_id, version)
        select tp.party_type  as entity_type,
               tp.identifier,
               tp.legal_name,
               tp.first_name,
               tp.middle_initial,
               tp.last_name,
               tp.title,
               tp.delivery_address_id,
               tp.mailing_address_id,
               tp.email,
               tp.party_id    as temp_party_id,
               tp.change_filing_id,
               tp.max_version as version
        from temp_parties_legal_name tp
        where tp.version = tp.max_version
          and not tp.is_business_party_colin_entity
          and not tp.is_proprietor_person
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
               tp.party_id    as temp_party_id,
               tp.change_filing_id,
               tp.max_version as version
        from temp_parties_legal_name tp
        where tp.version = tp.max_version
          and tp.is_business_party_colin_entity
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
with subquery as
         (select distinct tp.new_legal_entity_id as id,
                          tp.party_type          as entity_type,
                          tp.identifier,
                          tp.legal_name,
                          tp.first_name,
                          tp.middle_initial,
                          tp.last_name,
                          tp.title,
                          tp.delivery_address_id,
                          tp.mailing_address_id,
                          tp.email,
                          tp.version,
                          tp.change_filing_id,
                          tp.changed
          from temp_parties_legal_name tp
                   join (select party_id, max(version) as version
                         from temp_parties_legal_name
                         group by party_id) max_version
                        on tp.party_id = max_version.party_id
                   join temp_parties_legal_name maxTp
                        on max_version.party_id = maxTp.party_id and max_version.version = maxTp.version
          where not maxTp.is_business_party_colin_entity
            and not maxTp.is_proprietor_person),
     max_versions as
         (select id, max(version) as max_version
          from subquery sq
          group by id)
select sq.*
from subquery sq
         left join max_versions mv on mv.id = sq.id
where sq.version != mv.max_version;



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
with subquery as
         (select tp.new_legal_entity_id as id,
                 tp.identifier,
                 tp.organization_name,
                 tp.delivery_address_id,
                 tp.mailing_address_id,
                 tp.email,
                 tp.change_filing_id,
                 tp.changed,
                 tp.version
          from temp_parties_legal_name tp
                   join temp_parties_legal_name maxTp
                        on tp.party_id = maxTp.party_id and tp.max_version = maxTp.version
          where maxTp.is_business_party_colin_entity),
     max_versions as
         (select id, max(version) as max_version
          from subquery sq
          group by id)
select sq.*
from subquery sq
         left join max_versions mv on mv.id = sq.id
where sq.version != mv.max_version;


-- ************************************************************************************************
-- Inserts/Updates into legal_entities/legal_entities_history tables specific to natural person SPs
-- ************************************************************************************************

-- Update SP LE history entries that match party history entries using change filing id
-- update proprietor person record in legal_entities_history table using info from temp_parties_legal_name
with subquery AS
         (select CONCAT_WS(' ', NULLIF(tp.first_name, ''), NULLIF(tp.middle_initial, ''),
                           NULLIF(tp.last_name, '')) as legal_name,
                 tp.first_name,
                 tp.middle_initial,
                 tp.last_name,
                 tp.title,
                 tp.delivery_address_id,
                 tp.mailing_address_id,
                 tp.email,
                 tp.change_filing_id,
                 tp.new_legal_entity_id              as sp_legal_entity_id
          from temp_parties_legal_name tp
                   join legal_entities_history leh
                        on tp.new_legal_entity_id = leh.id and tp.change_filing_id = leh.change_filing_id
                   join (select party_id, max(version) as version
                         from temp_parties_legal_name
                         group by party_id) max_version
                        on tp.party_id = max_version.party_id
                   join temp_parties_legal_name maxTp
                        on max_version.party_id = maxTp.party_id and max_version.version = maxTp.version
          where 1 = 1
            and tp.is_proprietor_person
            AND tp.version <> maxTp.version)
update legal_entities_history leh
set entity_type         = 'person',
    legal_name          = CONCAT_WS(' ', NULLIF(sq.first_name, ''), NULLIF(sq.middle_initial, ''),
                                    NULLIF(sq.last_name, '')),
    first_name          = sq.first_name,
    middle_initial      = sq.middle_initial,
    last_name           = sq.last_name,
    title               = sq.title,
    delivery_address_id = sq.delivery_address_id,
    mailing_address_id  = sq.mailing_address_id,
    email               = sq.email
from subquery sq
WHERE leh.id = sq.sp_legal_entity_id
  AND leh.change_filing_id = sq.change_filing_id
;


-- Update SP LE entries that match party history entries using change filing id
-- update proprietor person record in legal_entities table using info from temp_parties_legal_name
with subquery AS
         (select CONCAT_WS(' ', NULLIF(tp.first_name, ''), NULLIF(tp.middle_initial, ''),
                           NULLIF(tp.last_name, '')) as legal_name,
                 tp.first_name,
                 tp.middle_initial,
                 tp.last_name,
                 tp.title,
                 tp.delivery_address_id,
                 tp.mailing_address_id,
                 tp.email,
                 tp.change_filing_id,
                 tp.new_legal_entity_id              as sp_legal_entity_id
          from temp_parties_legal_name tp
                   join legal_entities le
                        on tp.new_legal_entity_id = le.id and tp.change_filing_id = le.change_filing_id
                   join (select party_id, max(version) as version
                         from temp_parties_legal_name
                         group by party_id) max_version
                        on tp.party_id = max_version.party_id
                   join temp_parties_legal_name maxTp
                        on max_version.party_id = maxTp.party_id and max_version.version = maxTp.version
          where 1 = 1
            and tp.is_proprietor_person
            AND tp.version <> maxTp.version)
update legal_entities le
set entity_type         = 'person',
    legal_name          = CONCAT_WS(' ', NULLIF(sq.first_name, ''), NULLIF(sq.middle_initial, ''),
                                    NULLIF(sq.last_name, '')),
    first_name          = sq.first_name,
    middle_initial      = sq.middle_initial,
    last_name           = sq.last_name,
    title               = sq.title,
    delivery_address_id = sq.delivery_address_id,
    mailing_address_id  = sq.mailing_address_id,
    email               = sq.email
from subquery sq
WHERE le.id = sq.sp_legal_entity_id
  AND le.change_filing_id = sq.change_filing_id
;


-- For each entry in party_history table that has no matching change_filing_id in LE SP tables, find the most recent
-- SP LE history entry and combine with party data. bump the version number using prev entry version num as base.
-- Create a function to get the previous SP LE history entry
CREATE OR REPLACE FUNCTION get_previous_le_history_entry(le_id INT, change_filing_id_compare INT)
    RETURNS legal_entities_history AS
$$
DECLARE
    leh legal_entities_history%ROWTYPE;
BEGIN
    SELECT *
    INTO leh
    FROM legal_entities_history
    WHERE id = le_id
      AND change_filing_id < change_filing_id_compare
    ORDER BY leh.change_filing_id DESC
    LIMIT 1;
    RETURN leh;
EXCEPTION
    WHEN others THEN RAISE NOTICE '%', SQLERRM;
END;
$$ LANGUAGE plpgsql;



CREATE OR REPLACE FUNCTION insert_into_leh(base_leh legal_entities_history, updates jsonb)
    RETURNS VOID AS
$$
DECLARE
    key   text;
    value text;
BEGIN
    RAISE NOTICE 'insert_into_leh - 1';

    -- Loop through each key-value pair in the JSONB object
    FOR key, value IN SELECT * FROM jsonb_each_text(updates)
        LOOP
            -- Use a CASE statement to update the appropriate field based on the key
            CASE key
                WHEN 'id' THEN base_leh.id := value::int;
                WHEN 'legal_name' THEN base_leh.legal_name := value;
                WHEN 'first_name' THEN base_leh.first_name := value;
                WHEN 'middle_initial' THEN base_leh.middle_initial := value;
                WHEN 'last_name' THEN base_leh.last_name := value;
                WHEN 'title' THEN base_leh.title := value;
                WHEN 'delivery_address_id' THEN base_leh.delivery_address_id := value::int;
                WHEN 'mailing_address_id' THEN base_leh.mailing_address_id := value::int;
                WHEN 'email' THEN base_leh.email := value;
                WHEN 'change_filing_id' THEN base_leh.change_filing_id := value::int;
                WHEN 'changed' THEN base_leh.changed := value::timestamp;
                WHEN 'version' THEN base_leh.version := value::int;
                END CASE;
        END LOOP;

    -- Debug logging
    RAISE NOTICE 'Inserting into legal_entities_history with values: %', base_leh;

    -- Insert the leh record into the legal_entities_history table
    INSERT INTO legal_entities_history VALUES (base_leh.*);
EXCEPTION
    WHEN others THEN RAISE NOTICE '%', SQLERRM;
END;
$$ LANGUAGE plpgsql;



SELECT insert_into_leh(
               get_previous_le_history_entry(tp.new_legal_entity_id, tp.change_filing_id),
               jsonb_build_object(
                       'id', tp.new_legal_entity_id,
                       'legal_name', CONCAT_WS(' ', NULLIF(tp.first_name, ''), NULLIF(tp.middle_initial, ''),
                                               NULLIF(tp.last_name, '')),
                       'first_name', tp.first_name,
                       'middle_initial', tp.middle_initial,
                       'last_name', tp.last_name,
                       'title', tp.title,
                       'delivery_address_id', tp.delivery_address_id,
                       'mailing_address_id', tp.mailing_address_id,
                       'email', tp.email,
                       'change_filing_id', tp.change_filing_id,
                       'changed', tp.change_filing_effective_date,
                       'version', tp.version + 1
               )
       )
FROM temp_parties_legal_name tp
         LEFT JOIN legal_entities_history leh
                   ON tp.new_legal_entity_id = leh.id AND tp.change_filing_id = leh.change_filing_id
         LEFT JOIN legal_entities le
                   ON tp.new_legal_entity_id = le.id AND tp.change_filing_id = le.change_filing_id
         join (select party_id, max(version) as version
               from temp_parties_legal_name
               group by party_id) max_version
              on tp.party_id = max_version.party_id
         join temp_parties_legal_name maxTp
              on max_version.party_id = maxTp.party_id and max_version.version = maxTp.version
WHERE tp.is_proprietor_person
  AND le.change_filing_id IS NULL
  AND leh.change_filing_id IS NULL
  AND tp.version <> maxTp.version
order by tp.change_filing_id asc
    FETCH FIRST 10000000000 ROWS ONLY;
;


-- Update SP LE active entry if party entry matches change filing id
with subquery AS
         (select CONCAT_WS(' ', NULLIF(tp.first_name, ''), NULLIF(tp.middle_initial, ''),
                           NULLIF(tp.last_name, '')) as legal_name,
                 tp.first_name,
                 tp.middle_initial,
                 tp.last_name,
                 tp.title,
                 tp.delivery_address_id,
                 tp.mailing_address_id,
                 tp.email,
                 tp.change_filing_id,
                 tp.new_legal_entity_id              as sp_legal_entity_id
          from temp_parties_legal_name tp
                   join legal_entities le
                        on tp.new_legal_entity_id = le.id and tp.change_filing_id = le.change_filing_id
                   join (select party_id, max(version) as version
                         from temp_parties_legal_name
                         group by party_id) max_version
                        on tp.party_id = max_version.party_id
                   join temp_parties_legal_name maxTp
                        on max_version.party_id = maxTp.party_id and max_version.version = maxTp.version
          where 1 = 1
            and tp.is_proprietor_person
            AND tp.version = maxTp.version)
update legal_entities le
set entity_type         = 'person',
    legal_name          = CONCAT_WS(' ', NULLIF(sq.first_name, ''), NULLIF(sq.middle_initial, ''),
                                    NULLIF(sq.last_name, '')),
    first_name          = sq.first_name,
    middle_initial      = sq.middle_initial,
    last_name           = sq.last_name,
    title               = sq.title,
    delivery_address_id = sq.delivery_address_id,
    mailing_address_id  = sq.mailing_address_id,
    email               = sq.email
from subquery sq
WHERE le.id = sq.sp_legal_entity_id
  AND le.change_filing_id = sq.change_filing_id
;

-- Update SP LE history entry if party entry matches change filing id
with subquery AS
         (select CONCAT_WS(' ', NULLIF(tp.first_name, ''), NULLIF(tp.middle_initial, ''),
                           NULLIF(tp.last_name, '')) as legal_name,
                 tp.first_name,
                 tp.middle_initial,
                 tp.last_name,
                 tp.title,
                 tp.delivery_address_id,
                 tp.mailing_address_id,
                 tp.email,
                 tp.change_filing_id,
                 tp.new_legal_entity_id              as sp_legal_entity_id
          from temp_parties_legal_name tp
                   join legal_entities_history leh
                        on tp.new_legal_entity_id = leh.id and tp.change_filing_id = leh.change_filing_id
                   join (select party_id, max(version) as version
                         from temp_parties_legal_name
                         group by party_id) max_version
                        on tp.party_id = max_version.party_id
                   join temp_parties_legal_name maxTp
                        on max_version.party_id = maxTp.party_id and max_version.version = maxTp.version
          where 1 = 1
            and tp.is_proprietor_person
            AND tp.version = maxTp.version)
update legal_entities_history leh
set entity_type         = 'person',
    legal_name          = CONCAT_WS(' ', NULLIF(sq.first_name, ''), NULLIF(sq.middle_initial, ''),
                                    NULLIF(sq.last_name, '')),
    first_name          = sq.first_name,
    middle_initial      = sq.middle_initial,
    last_name           = sq.last_name,
    title               = sq.title,
    delivery_address_id = sq.delivery_address_id,
    mailing_address_id  = sq.mailing_address_id,
    email               = sq.email
from subquery sq
WHERE leh.id = sq.sp_legal_entity_id
  AND leh.change_filing_id = sq.change_filing_id
;

CREATE EXTENSION IF NOT EXISTS hstore;

CREATE OR REPLACE FUNCTION cast_le_to_leh(row_le legal_entities,
                                          ts timestamptz DEFAULT '1900-01-01T00:00:00Z'::timestamptz)
    RETURNS legal_entities_history
    LANGUAGE plpgsql AS
$$
DECLARE
    hstore_le  hstore;
    hstore_leh hstore;
    row_leh    legal_entities_history%ROWTYPE;
BEGIN

    RAISE NOTICE 'cast_le_to_leh - 1';
    -- Convert row_le to hstore
    hstore_le := hstore(row_le);

    -- Set the changed field
    hstore_leh := hstore_le || hstore(array ['changed'], array [ts::text]);

    -- Convert hstore_leh to legal_entities_history type
    row_leh := populate_record(NULL::legal_entities_history, hstore_leh);

    RETURN row_leh;
EXCEPTION
    WHEN others THEN RAISE NOTICE '%', SQLERRM;
END;
$$;


WITH unmatched_entries AS
         (SELECT tp.*
          FROM temp_parties_legal_name tp
                   LEFT JOIN legal_entities le
                             ON tp.new_legal_entity_id = le.id AND
                                tp.change_filing_id = le.change_filing_id
                   LEFT JOIN legal_entities_history leh
                             ON tp.new_legal_entity_id = leh.id AND
                                tp.change_filing_id = leh.change_filing_id
                   join (select party_id, max(version) as version
                         from temp_parties_legal_name
                         group by party_id) max_version
                        on tp.party_id = max_version.party_id
                   join temp_parties_legal_name maxTp
                        on max_version.party_id = maxTp.party_id and
                           max_version.version = maxTp.version
          WHERE tp.is_proprietor_person
            AND le.id IS NULL
            AND leh.id IS NULL
            AND tp.version = maxTp.version
            and tp.change_filing_id = 145024)
-- find the most recent legal_entities_history entry, relative to the change_filing_id
        ,
     previous_history_entries AS
         (SELECT leh.*
          FROM unmatched_entries ue
                   JOIN LATERAL (
              SELECT *
              FROM legal_entities_history
              WHERE id = ue.new_legal_entity_id
                AND change_filing_id < ue.change_filing_id
              ORDER BY change_filing_id DESC
              LIMIT 1
              ) leh ON TRUE),
     clone_and_insert AS
         (select ue.*
          FROM unmatched_entries ue
                   LEFT JOIN previous_history_entries phe ON ue.new_legal_entity_id = phe.id
          WHERE 1 = 1)
select *
from clone_and_insert
;


-- For each entry in temp_parties_legal_name table that has no matching change_filing_id in
-- legal_entities/legal_entities_history tables
WITH unmatched_entries AS
    (SELECT tp.*
     FROM temp_parties_legal_name tp
              LEFT JOIN legal_entities le
                        ON tp.new_legal_entity_id = le.id AND
                           tp.change_filing_id = le.change_filing_id
              LEFT JOIN legal_entities_history leh
                        ON tp.new_legal_entity_id = leh.id AND
                           tp.change_filing_id = leh.change_filing_id
              join (select party_id, max(version) as version
                    from temp_parties_legal_name
                    group by party_id) max_version
                   on tp.party_id = max_version.party_id
              join temp_parties_legal_name maxTp
                   on max_version.party_id = maxTp.party_id and
                      max_version.version = maxTp.version
     WHERE tp.is_proprietor_person
       AND le.id IS NULL
       AND leh.id IS NULL
       AND tp.version = maxTp.version)
-- find the most recent legal_entities_history entry, relative to the change_filing_id
   , previous_history_entries AS
    (SELECT leh.*
     FROM unmatched_entries ue
              JOIN LATERAL (
         SELECT *
         FROM legal_entities_history
         WHERE id = ue.new_legal_entity_id
           AND change_filing_id < ue.change_filing_id
         ORDER BY change_filing_id DESC
         LIMIT 1
         ) leh ON TRUE)
-- if no match, clone LE SP active entry and INSERT into history table, update active row using party entry.  bump the
-- version number using prev entry version num as base
   , clone_and_insert AS
    (SELECT insert_into_leh(
                    (SELECT cast_le_to_leh(le.*, prev_tp.changed)
                     FROM legal_entities le
                              join temp_parties_legal_name prev_tp on le.id = prev_tp.new_legal_entity_id and
                                                                      le.change_filing_id = prev_tp.change_filing_id
                     WHERE le.id = ue.new_legal_entity_id),
                    jsonb_build_object(
                            'version', 1
                    )
            )
     FROM unmatched_entries ue
              LEFT JOIN previous_history_entries phe ON ue.new_legal_entity_id = phe.id
     WHERE phe.id IS NULL)
   , update_active_row AS
    (UPDATE legal_entities le
        SET entity_type = 'person',
            legal_name =
                    CONCAT_WS(' ', NULLIF(ue.first_name, ''), NULLIF(ue.middle_initial, ''), NULLIF(ue.last_name, '')),
            first_name = ue.first_name,
            middle_initial = ue.middle_initial,
            last_name = ue.last_name,
            title = ue.title,
            delivery_address_id = ue.delivery_address_id,
            mailing_address_id = ue.mailing_address_id,
            email = ue.email,
            version = 2,
            change_filing_id = ue.change_filing_id
        FROM unmatched_entries ue
            LEFT JOIN previous_history_entries phe ON ue.new_legal_entity_id = phe.id
        WHERE le.id = ue.new_legal_entity_id and phe.id is NULL)
   ,
-- if match, create new SP LE history entry and combine with party data.  bump the version number using prev entry version num as base
    create_new_history_entry AS
        (SELECT insert_into_leh(
                        phe.*,
                        jsonb_build_object(
                                'id', ue.new_legal_entity_id,
                                'legal_name', CONCAT_WS(' ', NULLIF(ue.first_name, ''), NULLIF(ue.middle_initial, ''),
                                                        NULLIF(ue.last_name, '')),
                                'first_name', ue.first_name,
                                'middle_initial', ue.middle_initial,
                                'last_name', ue.last_name,
                                'title', ue.title,
                                'delivery_address_id', ue.delivery_address_id,
                                'mailing_address_id', ue.mailing_address_id,
                                'email', ue.email,
                                'change_filing_id', ue.change_filing_id,
                                'changed', ue.change_filing_effective_date,
                                'version', phe.version + 1
                        )
                )
         FROM unmatched_entries ue
                  JOIN previous_history_entries phe ON ue.new_legal_entity_id = phe.id)
SELECT COUNT(*)
FROM (SELECT *
      FROM clone_and_insert
      UNION ALL
      SELECT *
      FROM create_new_history_entry) AS temp
;


-- For each entry in LE SP history table that does not have matching party/party_history change_filing_id, find
-- previous record to load required person info and update version num
DO
$$
    DECLARE
        rec RECORD;
    BEGIN
        FOR rec IN (SELECT *
                    FROM legal_entities_history leh
                             LEFT JOIN temp_parties_legal_name tp
                                       ON leh.id = tp.new_legal_entity_id AND
                                          leh.change_filing_id = tp.change_filing_id
                    WHERE tp.new_legal_entity_id IS NULL
                    ORDER BY leh.change_filing_id)
            LOOP
                -- find previous record to load required person info
                WITH previous_leh_entries AS
                         (SELECT *
                          FROM legal_entities_history
                          WHERE id = rec.id
                            AND change_filing_id < rec.change_filing_id
                          ORDER BY change_filing_id DESC
                          LIMIT 1)
                -- update fields using previous leh entry
                UPDATE legal_entities_history leh
                SET version             = ple.version + 1,
                    legal_name          = ple.legal_name,
                    first_name          = ple.first_name,
                    middle_initial      = ple.middle_initial,
                    last_name           = ple.last_name,
                    title               = ple.title,
                    delivery_address_id = ple.delivery_address_id,
                    mailing_address_id  = ple.mailing_address_id,
                    email               = ple.email,
                    entity_type         = ple.entity_type
                FROM previous_leh_entries ple
                WHERE leh.id = rec.id
                  AND leh.change_filing_id = rec.change_filing_id;
            END LOOP;
    END;
$$;


-- Resort all SP LE history entries by id and change_filing_id and recalculate version nums
WITH sorted_entries AS (SELECT id,
                               change_filing_id,
                               ROW_NUMBER() OVER (PARTITION BY id ORDER BY change_filing_id) as new_version
                        FROM legal_entities_history)
UPDATE legal_entities_history leh
SET version = se.new_version
FROM sorted_entries se
WHERE leh.id = se.id
  AND leh.change_filing_id = se.change_filing_id
;


-- For each LE SP active entry, find the most recent LE SP history record
--    1. if no LE SP history record exists, do nothing.
--    2. if LE SP history record is found and there is no match in party or party history tables, copy person info from LE SP history record and bump version num from LE SP history record.
--    3. if LE SP history record is found and there is a match is found in party or party history tables, just bump the version num of the active LE SP record using the history record

CREATE TABLE recent_history AS (SELECT leh.id, MAX(leh.change_filing_id) as max_change_filing_id
                                FROM legal_entities_history leh
                                GROUP BY leh.id);

CREATE TABLE recent_history_details AS (SELECT leh.*
                                        FROM legal_entities_history leh
                                                 JOIN recent_history rh
                                                      ON leh.id = rh.id AND leh.change_filing_id = rh.max_change_filing_id);

CREATE TABLE party_matches AS (SELECT le.id, tp.party_id
                               FROM legal_entities le
                                        LEFT JOIN temp_parties_legal_name tp ON le.id = tp.new_legal_entity_id AND
                                                                                le.change_filing_id =
                                                                                tp.change_filing_id);

-- if LE SP history record is found and there is no match in party or party history tables, copy person info from
-- LE SP history record and bump version num from LE SP history record.
UPDATE legal_entities le
SET version             = combined.rhd_version + 1,
    legal_name          = COALESCE(le.legal_name, combined.rhd_legal_name),
    first_name          = COALESCE(le.first_name, combined.rhd_first_name),
    middle_initial      = COALESCE(le.middle_initial, combined.rhd_middle_initial),
    last_name           = COALESCE(le.last_name, combined.rhd_last_name),
    title               = COALESCE(le.title, combined.rhd_title),
    delivery_address_id = COALESCE(le.delivery_address_id, combined.rhd_delivery_address_id),
    mailing_address_id  = COALESCE(le.mailing_address_id, combined.rhd_mailing_address_id),
    email               = COALESCE(le.email, combined.rhd_email),
    entity_type         = combined.rhd_entity_type
FROM (SELECT le.*,
             rhd.version             as rhd_version,
             rhd.legal_name          as rhd_legal_name,
             rhd.first_name          as rhd_first_name,
             rhd.middle_initial      as rhd_middle_initial,
             rhd.last_name           as rhd_last_name,
             rhd.title               as rhd_title,
             rhd.delivery_address_id as rhd_delivery_address_id,
             rhd.mailing_address_id  as rhd_mailing_address_id,
             rhd.email               as rhd_email,
             rhd.entity_type         as rhd_entity_type,
             pm.party_id
      FROM legal_entities le
               JOIN recent_history_details rhd ON le.id = rhd.id
               LEFT JOIN party_matches pm ON le.id = pm.id) AS combined
WHERE le.id = combined.id
  AND combined.party_id IS NULL;

-- if LE SP history record is found and there is a match is found in party or party history tables, just bump the
-- version num of the active LE SP record using the history record
UPDATE legal_entities le
SET version = combined.rhd_version + 1
FROM (SELECT le.*,
             rhd.version             as rhd_version,
             rhd.legal_name          as rhd_legal_name,
             rhd.first_name          as rhd_first_name,
             rhd.middle_initial      as rhd_middle_initial,
             rhd.last_name           as rhd_last_name,
             rhd.title               as rhd_title,
             rhd.delivery_address_id as rhd_delivery_address_id,
             rhd.mailing_address_id  as rhd_mailing_address_id,
             rhd.email               as rhd_email,
             rhd.entity_type         as rhd_entity_type,
             pm.party_id
      FROM legal_entities le
               JOIN recent_history_details rhd ON le.id = rhd.id
               LEFT JOIN party_matches pm ON le.id = pm.id) AS combined
WHERE le.id = combined.id
  AND combined.party_id IS NOT NULL;


DROP TABLE recent_history;
DROP TABLE recent_history_details;
DROP TABLE party_matches;

-- ************************************************************************************************
-- PARTY_ROLES/PARTY_ROLES_history -> ENTIYTY_ROLES/ENTITY_ROLES_history
-- ************************************************************************************************

CREATE TABLE temp_party_roles_legal_name AS
select pr.id                 as party_role_id,
       CAST(NULL AS INTEGER) as new_entity_role_id,
       pr.role::roletypes    as role_type,
       pr.appointment_date,
       pr.cessation_date,
       pr.legal_entity_id,
       pr.party_id,
       pr.filing_id,
       pr.change_filing_id,
       f.effective_date      as changed,
       pr.version,
       pr.version            as max_version
from party_roles pr
         left join filings f on pr.change_filing_id = f.id
where pr.role is not null
  and pr.role <> ''
UNION
select prh.id                as party_role_id,
       CAST(NULL AS INTEGER) as new_entity_role_id,
       prh.role::roletypes   as role_type,
       prh.appointment_date,
       prh.cessation_date,
       prh.legal_entity_id,
       prh.party_id,
       prh.filing_id,
       prh.change_filing_id,
       prh.changed,
       prh.version,
       cpr.version           as max_version
from party_roles_history prh
         join party_roles cpr on cpr.id = prh.id
where prh.role is not null
  and prh.role <> ''
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
                 join temp_parties_legal_name tp on tpr.party_id = tp.party_id and tp.version = tp.max_version
        where tpr.version = tpr.max_version
          and not tp.is_business_party_colin_entity
          and not tp.is_resolution_party
          and not tp.is_proprietor_person
        RETURNING id, temp_party_role_id, temp_party_id)
UPDATE temp_party_roles_legal_name
set new_entity_role_id = ibper.id
from insert_parties_entity_role ibper
where temp_party_roles_legal_name.party_role_id = ibper.temp_party_role_id
;


-- insert all version records business party persons associations into entity_roles_history table
INSERT INTO entity_roles_history (id, role_type, legal_entity_id, related_entity_id, appointment_date, cessation_date,
                                  filing_id, change_filing_id, changed, version)
with subquery as
         (select distinct tpr.new_entity_role_id as id,
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
                   join temp_parties_legal_name tp on tpr.party_id = tp.party_id and tp.version = tp.max_version
          where not tp.is_business_party_colin_entity
            and not tp.is_resolution_party
            and not tp.is_proprietor_person),
     max_versions as
         (select id, max(version) as max_version
          from subquery sq
          group by id)
select sq.*
from subquery sq
         left join max_versions mv on mv.id = sq.id
where sq.cessation_date is not null
   or sq.version != mv.max_version;


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
                 join temp_parties_legal_name tp on tpr.party_id = tp.party_id and tp.version = tp.max_version
        where tpr.version = tpr.max_version
          and tp.is_business_party_colin_entity
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
with subquery as
         (select distinct tpr.new_entity_role_id as id,
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
                   join temp_parties_legal_name tp on tpr.party_id = tp.party_id and tp.version = tp.max_version
          where tp.is_business_party_colin_entity
            and not tp.is_resolution_party),
     max_versions as
         (select id, max(version) as max_version
          from subquery sq
          group by id)
select sq.*
from subquery sq
         left join max_versions mv on mv.id = sq.id
where sq.cessation_date is not null
   or sq.version != mv.max_version;


delete
from entity_roles
where cessation_date is not null;

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


-- Update all 'fromLegalName' keys to 'fromBusinessName' in meta_data column of filings table
update filings
set meta_data = rename_jsonb_key(meta_data, 'fromLegalName', 'fromBusinessName');

-- Update all 'toLegalName' keys to 'toBusinessName' in meta_data column of filings table
update filings
set meta_data = rename_jsonb_key(meta_data, 'toLegalName', 'toBusinessName');


-- copy all legal name key/value pairs found in filing_json -> 'filing' -> 'business' -> 'legalName'
-- into a new key on the business block called 'businessName'
UPDATE filings
SET filing_json = jsonb_set(filing_json,
                            '{filing,business,businessName}',
                            to_jsonb(filing_json -> 'filing' -> 'business' ->> 'legalName'))
WHERE filing_json -> 'filing' -> 'business' ? 'legalName'
;


-- updating all firm legal names to be null.
-- TODO: populate with right legal names for firms once scripts handle new way of cutting party rows
UPDATE filings
SET filing_json = jsonb_set(filing_json, '{filing,business,legalName}', 'null', false)
WHERE filing_json -> 'filing' -> 'business' ? 'legalName'
  and filing_json -> 'filing' -> 'business' ? 'legalType'
  and filing_json -> 'filing' -> 'business' ->> 'legalType' in ('SP', 'GP');


CREATE OR REPLACE FUNCTION update_legal_name() RETURNS VOID AS
$$
DECLARE
    rec            RECORD;
    legal_name_str TEXT;
    results        RECORD;
    result_count   INTEGER;
BEGIN
    FOR rec IN SELECT * FROM legal_entities WHERE entity_type IN ('GP')
        LOOP
            result_count := 0;
            legal_name_str := '';
            FOR results IN (SELECT temp_ln_concat."legalName"
                            FROM (SELECT CASE
                                             WHEN (related_le_alias.entity_type = 'person') THEN concat_ws(' ',
                                                                                                           nullif(related_le_alias.first_name, ''),
                                                                                                           nullif(related_le_alias.middle_initial, ''),
                                                                                                           nullif(related_le_alias.last_name, ''))
                                             WHEN (related_le_alias.entity_type = 'organization')
                                                 THEN related_le_alias.legal_name
                                             END AS "legalName"
                                  FROM legal_entities
                                           JOIN entity_roles ON entity_roles.legal_entity_id = legal_entities.id
                                           JOIN legal_entities AS related_le_alias
                                                ON related_le_alias.id = entity_roles.related_entity_id
                                  WHERE legal_entities.id = rec.id
                                  UNION
                                  SELECT colin_entities.organization_name AS "legalName"
                                  FROM legal_entities
                                           JOIN entity_roles ON entity_roles.legal_entity_id = legal_entities.id
                                           JOIN colin_entities
                                                ON colin_entities.id = entity_roles.related_colin_entity_id
                                  WHERE legal_entities.id = rec.id) AS temp_ln_concat
                            ORDER BY temp_ln_concat."legalName")
                LOOP
                    result_count := result_count + 1;
                    IF result_count <= 2 THEN
                        legal_name_str := legal_name_str || results."legalName" || ', ';
                    ELSE
                        legal_name_str := legal_name_str || 'et al';
                        EXIT; -- Exit the loop after processing the first two results
                    END IF;
                END LOOP;
            legal_name_str := rtrim(legal_name_str, ', '); -- Remove trailing comma and space
            UPDATE legal_entities SET legal_name = legal_name_str WHERE id = rec.id;
        END LOOP;
    update legal_entities
    set legal_name = concat_ws(' ',
                               nullif(first_name, ''),
                               nullif(middle_initial, ''),
                               nullif(last_name, ''))
    where entity_type = 'person';

END;
$$ LANGUAGE plpgsql;

SELECT update_legal_name();

-- TODO: create update_legal_name_history() to update legal_name for legal_entities_history


-- Move all associations for SP(firm owner is person or firm owner is org(LEAR or COLIN) LE records to
-- alternate names table
UPDATE filings f
SET alternate_name_id = an.id,
    legal_entity_id   = NULL
FROM alternate_names an
         JOIN legal_entities le ON an.legal_entity_id = le.id
WHERE f.legal_entity_id = le.id
  AND an.name_type = 'DBA'
  AND an.entity_type = 'SP'
  AND le.entity_type in ('SP', 'person');


UPDATE comments c
SET alternate_name_id = an.id,
    legal_entity_id   = NULL
FROM alternate_names an
         JOIN legal_entities le ON an.legal_entity_id = le.id
WHERE c.legal_entity_id = le.id
  AND an.name_type = 'DBA'
  AND an.entity_type = 'SP'
  AND le.entity_type in ('SP', 'person');


UPDATE request_tracker rt
SET alternate_name_id = an.id,
    legal_entity_id   = NULL
FROM alternate_names an
         JOIN legal_entities le ON an.legal_entity_id = le.id
WHERE rt.legal_entity_id = le.id
  AND an.name_type = 'DBA'
  AND an.entity_type = 'SP'
  AND le.entity_type in ('SP', 'person');


UPDATE dc_connections dcc
SET alternate_name_id = an.id,
    legal_entity_id   = NULL
FROM alternate_names an
         JOIN legal_entities le ON an.legal_entity_id = le.id
WHERE dcc.legal_entity_id = le.id
  AND an.name_type = 'DBA'
  AND an.entity_type = 'SP'
  AND le.entity_type in ('SP', 'person');


UPDATE dc_issued_business_user_credentials dcibuuc
SET alternate_name_id = an.id,
    legal_entity_id   = NULL
FROM alternate_names an
         JOIN legal_entities le ON an.legal_entity_id = le.id
WHERE dcibuuc.legal_entity_id = le.id
  AND an.name_type = 'DBA'
  AND an.entity_type = 'SP'
  AND le.entity_type in ('SP', 'person');


UPDATE documents_history dh
SET alternate_name_id = an.id,
    legal_entity_id   = NULL
FROM alternate_names an
         JOIN legal_entities le ON an.legal_entity_id = le.id
WHERE dh.legal_entity_id = le.id
  AND an.name_type = 'DBA'
  AND an.entity_type = 'SP'
  AND le.entity_type in ('SP', 'person');

UPDATE documents d
SET alternate_name_id = an.id,
    legal_entity_id   = NULL
FROM alternate_names an
         JOIN legal_entities le ON an.legal_entity_id = le.id
WHERE d.legal_entity_id = le.id
  AND an.name_type = 'DBA'
  AND an.entity_type = 'SP'
  AND le.entity_type in ('SP', 'person');


UPDATE offices o
SET alternate_name_id = an.id,
    legal_entity_id   = NULL
FROM alternate_names an
         JOIN legal_entities le ON an.legal_entity_id = le.id
WHERE o.legal_entity_id = le.id
  AND an.name_type = 'DBA'
  AND an.entity_type = 'SP'
  AND le.entity_type in ('SP', 'person');


UPDATE offices_history oh
SET alternate_name_id = an.id,
    legal_entity_id   = NULL
FROM alternate_names an
         JOIN legal_entities le ON an.legal_entity_id = le.id
WHERE oh.legal_entity_id = le.id
  AND an.name_type = 'DBA'
  AND an.entity_type = 'SP'
  AND le.entity_type in ('SP', 'person');


-- Link alternate_name_id to custodial address in addresses/addresses_history
WITH subquery AS (SELECT a.id AS address_id,
                         o.alternate_name_id
                  FROM addresses a
                           JOIN offices o
                                ON a.office_id = o.id
                  WHERE a.office_id IS NOT NULL
                    AND o.office_type = 'custodialOffice')
UPDATE addresses a
SET alternate_name_id = sq.alternate_name_id,
    legal_entity_id   = NULL
FROM subquery sq
WHERE a.id = sq.address_id
  AND sq.alternate_name_id IS NOT NULL;

WITH subquery AS (SELECT ah.id,
                         oh.alternate_name_id
                  FROM addresses_history ah
                           JOIN offices_history oh
                                ON ah.office_id = oh.id
                  WHERE ah.office_id IS NOT NULL
                    AND oh.office_type = 'custodialOffice')
UPDATE addresses_history ah
SET alternate_name_id = sq.alternate_name_id,
    legal_entity_id   = NULL
FROM subquery sq
WHERE ah.id = sq.id
  AND sq.alternate_name_id IS NOT NULL;


CREATE TABLE temp_sp_person_entity_role AS
select le.id          as sp_id,
       le.entity_type as sp_entity_type,
       le.identifier  as sp_identifer,
       le.first_name,
       le.middle_initial,
       le.last_name,
       le.legal_name
from legal_entities le
where le.entity_type = 'SP'
  and (first_name is not null or middle_initial is not null or last_name is not null);

update legal_entities_history leh
set entity_type = 'person'
where leh.id in (select sp_id from temp_sp_person_entity_role);

update legal_entities le
set entity_type = 'person'
where le.id in (select sp_id from temp_sp_person_entity_role);


-- Move remaining SP DBA LEAR associations that need to reside with alternate_names
CREATE TABLE temp_sp_dba_entity_role AS
select le.id                   as sp_id,
       le.entity_type          as sp_entity_type,
       le.identifier           as sp_identifer,
       er.id                   as er_id,
       er.role_type            as er_role_type,
       ler.id                  as related_entity_id,
       ler.entity_type         as related_entity_type,
       ler.identifier          as related_identifier,
       ler.delivery_address_id as related_delivery_address_id,
       ler.mailing_address_id  as related_mailing_address_id,
       ler.email               as related_email,
       le_match.id             as le_match_id,
       le_match.entity_type    as le_match_entity_type
from legal_entities le
         join entity_roles er on le.id = er.legal_entity_id
         join legal_entities ler on er.related_entity_id = ler.id
         left join legal_entities le_match on le_match.identifier = ler.identifier and
                                              le_match.entity_type in ('CP', 'BEN', 'BC', 'ULC', 'CC', 'SP', 'GP')
where le.entity_type = 'SP'
  and er.role_type = 'proprietor'
  and ler.entity_type = 'organization'
  and ler.identifier is not null
  and ler.identifier <> '';


UPDATE alternate_names an
SET legal_entity_id     = temp.le_match_id,
    delivery_address_id = temp.related_delivery_address_id,
    mailing_address_id  = temp.related_mailing_address_id,
    email               = temp.related_email
FROM (SELECT sp_id,
             le_match_id,
             related_delivery_address_id,
             related_mailing_address_id,
             related_email
      FROM temp_sp_dba_entity_role) AS temp
WHERE an.legal_entity_id = temp.sp_id;


-- TODO update alternate_names_history entry to use corresponding address & email for SP LEAR DBA

UPDATE alternate_names_history anh
SET legal_entity_id = temp.le_match_id
FROM (SELECT sp_id, le_match_id
      FROM temp_sp_dba_entity_role) AS temp
WHERE anh.legal_entity_id = temp.sp_id;


DELETE
FROM entity_roles_history
WHERE id IN (SELECT er_id
             FROM temp_sp_dba_entity_role);

DELETE
FROM entity_roles
WHERE id IN (SELECT er_id
             FROM temp_sp_dba_entity_role);

DELETE
FROM legal_entities_history
WHERE id IN (SELECT related_entity_id
             FROM temp_sp_dba_entity_role);

DELETE
FROM legal_entities
WHERE id IN (SELECT related_entity_id
             FROM temp_sp_dba_entity_role);

DELETE
FROM party_roles
WHERE legal_entity_id IN (SELECT sp_id
                          FROM temp_sp_dba_entity_role);

-- TODO: can be removed once address info is moved to alternate name entry
DELETE
FROM offices_history
WHERE legal_entity_id IN (SELECT sp_id
                          FROM temp_sp_dba_entity_role);

DELETE
FROM offices
WHERE legal_entity_id IN (SELECT sp_id
                          FROM temp_sp_dba_entity_role);

DELETE
FROM legal_entities_history
WHERE id IN (SELECT sp_id
             FROM temp_sp_dba_entity_role);

DELETE
FROM legal_entities
WHERE id IN (SELECT sp_id
             FROM temp_sp_dba_entity_role);


-- Move remaining SP DBA COLIN associations that need to reside with alternate_names
CREATE TABLE temp_sp_dba_colin_entity_role AS
select le.id                  as sp_id,
       le.entity_type         as sp_entity_type,
       le.identifier          as sp_identifer,
       er.id                  as er_id,
       er.role_type           as er_role_type,
       ce.id                  as related_colin_entity_id,
       ce.identifier          as related_colin_identifier,
       ce.delivery_address_id as related_delivery_address_id,
       ce.mailing_address_id  as related_mailing_address_id,
       ce.email               as related_email
from legal_entities le
         join entity_roles er on le.id = er.legal_entity_id
         join colin_entities ce on er.related_colin_entity_id = ce.id
where le.entity_type = 'SP'
  and er.role_type = 'proprietor';


UPDATE alternate_names an
SET legal_entity_id     = null,
    colin_entity_id     = related_colin_entity_id,
    delivery_address_id = related_delivery_address_id,
    mailing_address_id  = related_mailing_address_id,
    email               = related_email
FROM (SELECT sp_id,
             related_colin_entity_id,
             related_delivery_address_id,
             related_mailing_address_id,
             related_email
      FROM temp_sp_dba_colin_entity_role) AS temp
WHERE an.legal_entity_id = temp.sp_id;


-- TODO update alternate_names_history entry to use corresponding address & email for SP COLIN DBA

UPDATE alternate_names_history anh
SET legal_entity_id = null,
    colin_entity_id = related_colin_entity_id
FROM (SELECT sp_id, related_colin_entity_id
      FROM temp_sp_dba_colin_entity_role) AS temp
WHERE anh.legal_entity_id = temp.sp_id;


DELETE
FROM entity_roles_history
WHERE id IN (SELECT er_id
             FROM temp_sp_dba_colin_entity_role);

DELETE
FROM entity_roles
WHERE id IN (SELECT er_id
             FROM temp_sp_dba_colin_entity_role);


DELETE
FROM party_roles
WHERE legal_entity_id IN (SELECT sp_id
                          FROM temp_sp_dba_colin_entity_role);

-- TODO: can be removed once address info is moved to alternate name entry
DELETE
FROM offices_history
WHERE legal_entity_id IN (SELECT sp_id
                          FROM temp_sp_dba_colin_entity_role);

DELETE
FROM offices
WHERE legal_entity_id IN (SELECT sp_id
                          FROM temp_sp_dba_colin_entity_role);

DELETE
FROM legal_entities_history
WHERE id IN (SELECT sp_id
             FROM temp_sp_dba_colin_entity_role);

DELETE
FROM legal_entities
WHERE id IN (SELECT sp_id
             FROM temp_sp_dba_colin_entity_role);


-- Set fields that do not need to be populated for proprietor individuals to null
update public.legal_entities
set naics_key=null,
    naics_code=null,
    naics_description=null,
    dissolution_date=null,
    identifier=null,
    state=null,
    state_filing_id=null,
    start_date=null
where id in (select id from legal_entities le where le.entity_type = 'person' and le.identifier like 'FM%');


update public.legal_entities_history
set naics_key=null,
    naics_code=null,
    naics_description=null,
    dissolution_date=null,
    identifier=null,
    state=null,
    state_filing_id=null,
    start_date=null
where id in (select id from legal_entities_history le where le.entity_type = 'person' and le.identifier like 'FM%');


-- Update all identifiers for person LEs in legal_entities to use format 'P1234567'
UPDATE legal_entities
SET identifier = 'P' || LPAD(nextval('legal_entity_identifier_person')::text, 7, '0')
WHERE LOWER(entity_type) = 'person';


-- Update all identifiers for person LEs in legal_entities_history with corresponding identifiers in legal_entities
WITH legal_entities_person AS (SELECT leh.id,
                                      le.identifier,
                                      le.entity_type
                               FROM legal_entities_history leh
                                        LEFT JOIN legal_entities le ON leh.id = le.id)
UPDATE legal_entities_history leh
SET identifier  = lep.identifier,
    entity_type = lep.entity_type
FROM legal_entities_person lep
WHERE leh.id = lep.id
  AND LOWER(lep.entity_type) = 'person';


-- Update all identifiers for person LEs that only exist in legal_entities_history
WITH legal_entities_history_person AS (SELECT temp.id,
                                              nextval('legal_entity_identifier_person') as seq_value
                                       FROM (SELECT DISTINCT leh.id
                                             FROM legal_entities_history leh
                                             WHERE leh.identifier IS NULL
                                               and LOWER(leh.entity_type) = 'person') AS temp)
UPDATE legal_entities_history leh
SET identifier = 'P' || LPAD(seq_value::text, 7, '0')
FROM legal_entities_history_person lehp
WHERE leh.id = lehp.id;


-- DROP temporarily created columns, functions and tables
DROP TABLE temp_legal_name_changes;
DROP TABLE temp_parties_legal_name;
DROP TABLE temp_party_roles_legal_name;
DROP TABLE temp_sp_person_entity_role;
DROP TABLE temp_sp_dba_entity_role;
DROP TABLE temp_sp_dba_colin_entity_role;
DROP FUNCTION has_non_legal_name_change;
DROP FUNCTION update_filing_json_party_ids;
DROP FUNCTION rename_jsonb_key;
DROP FUNCTION update_legal_name;
DROP FUNCTION cast_le_to_leh;
DROP FUNCTION get_previous_le_history_entry;
DROP FUNCTION insert_into_leh;
DROP EXTENSION hstore;
ALTER TABLE legal_entities
    DROP COLUMN temp_party_id;
ALTER TABLE colin_entities
    DROP COLUMN temp_party_id;
ALTER TABLE entity_roles
    DROP COLUMN temp_party_role_id;
ALTER TABLE entity_roles
    DROP COLUMN temp_party_id;


VACUUM FULL;
