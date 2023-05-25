-- Description:
-- Script to migrate data related to legal name model changes.
-- Summary of changes:
-- 1. Migrate SP/GP legal name(legal_entities.legal_name/legal_entities_version.legal_name) entries to
--    alternate_names/alternate_names_version tables.  The migrated entries were actually operating names and not legal
--    names.
-- 2. Remove legal_entities_version entries that were only name changes.  These should only reside in
--    alternate_names_version tables.  As a part of this update, the end transaction ids needed to be re-linked
--    to ensure that the history can still be traversed properly.


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
        where 1 = 1
          and f_next_tmp.legal_entity_id = lev.id
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
        where 1 = 1
          and f_next_tmp.legal_entity_id = lev.id
          and f_next_tmp.transaction_id > lev.transaction_id
        order by f_next_tmp.transaction_id asc
        limit 1)                                          as end_transaction_id,
       prev_lev.end_transaction_id                        as prev_end_transaction_id
from legal_entities_version lev
         join transaction t on lev.transaction_id = t.id
         left join filings f on f.transaction_id = lev.transaction_id
         left join legal_entities_version prev_lev
                   on lev.transaction_id = prev_lev.end_transaction_id
where 1 = 1
  and lev.entity_type in ('SP', 'GP')
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
from temp_legal_name_changes lnc join (select max(transaction_id) as transaction_id
                                       from temp_legal_name_changes lnc
                                       where lnc.filing_id is not null and lnc.legal_name_changed = True
                                       group by identifier
) max_transaction on lnc.transaction_id = max_transaction.transaction_id
where 1 = 1
  and lnc.filing_id is not null
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
where 1 = 1
  and lnc.filing_id is not null
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
                            where 1 = 1
                              and f_next_tmp.legal_entity_id = lev.id
                              and f_next_tmp.transaction_id > lev.transaction_id
                            order by f_next_tmp.transaction_id asc
                            limit 1) as end_transaction_id
                    from legal_entities_version lev
                             join transaction t on lev.transaction_id = t.id
                             left join filings f on f.transaction_id = lev.transaction_id
                    where 1 = 1
                      and lev.entity_type in ('SP', 'GP')
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


-- DROP temporarily created functions and tables
DROP TABLE IF EXISTS temp_legal_name_changes;
DROP FUNCTION has_non_legal_name_change;

