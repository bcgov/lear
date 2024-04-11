-- ****************************************************************
-- aliases_version reference orphaned business entry
-- ****************************************************************

-- create temp table for alias ids to delete
CREATE TEMP TABLE temp_alias_ids AS
select distinct av.id
from aliases_version av
         left join businesses b on av.business_id = b.id
where av.business_id is not null
  and b.id is null;


-- backup data to be deleted
copy (
    select distinct av.*
    from aliases_version av
    where id in (select id from temp_alias_ids))
    TO '/tmp/16902_orphaned_data__aliases_version.csv' WITH (FORMAT CSV, HEADER);

copy (
    select distinct a.*
    from aliases a
    where id in (select id from temp_alias_ids))
    TO '/tmp/16902_orphaned_data__aliases.csv' WITH (FORMAT CSV, HEADER);

-- delete orphaned entries
delete
from aliases_version
where id in (select id from temp_alias_ids);

delete
from aliases
where id in (select id from temp_alias_ids);


-- verification i.e. cnt == 0
select count(1) as cnt
from aliases_version av
where id in (select id from temp_alias_ids);

select count(1) as cnt
from aliases a
where id in (select id from temp_alias_ids);

drop table temp_alias_ids;

-- ****************************************************************
-- offices_history reference orphaned business entry
-- ****************************************************************

-- create temp table for offices_version ids to delete
CREATE TEMP TABLE temp_offices_ids AS
select distinct ov.id
from offices_version ov
         left join businesses b on ov.business_id = b.id
where ov.business_id is not null
  and b.id is null;


-- backup data to be deleted
copy (
    select distinct ov.*
    from offices_version ov
    where id in (select id from temp_offices_ids))
    TO '/tmp/16902_orphaned_data__offices_version.csv' WITH (FORMAT CSV, HEADER);

copy (
    select distinct o.*
    from offices o
    where id in (select id from temp_offices_ids))
    TO '/tmp/16902_orphaned_data__offices.csv' WITH (FORMAT CSV, HEADER);


-- delete orphaned entries
delete
from offices_version
where id in (select id from temp_offices_ids);

delete
from offices
where id in (select id from temp_offices_ids);


-- verification i.e. cnt == 0
select count(1) as cnt
from offices_version ov
where id in (select id from temp_offices_ids);

select count(1) as cnt
from offices o
where id in (select id from temp_offices_ids);

drop table temp_offices_ids;

-- ****************************************************************
-- addresses_history reference orphaned business entry
-- ****************************************************************

-- create temp table for address ids to delete
CREATE TEMP TABLE temp_address_ids_business_fk AS
select distinct av.id
from addresses_version av
         left join businesses b on av.business_id = b.id
where av.business_id is not null
  and b.id is null;

select *
from temp_address_ids_business_fk;

-- backup data to be deleted
copy (
    select distinct av.*
    from addresses_version av
    where id in (select id from temp_address_ids_business_fk))
    TO '/tmp/16902_orphaned_data__addresses_version_fk_business.csv' WITH (FORMAT CSV, HEADER);

copy (
    select distinct a.*
    from addresses a
    where id in (select id from temp_address_ids_business_fk))
    TO '/tmp/16902_orphaned_data__addresses_fk_business.csv' WITH (FORMAT CSV, HEADER);


-- delete orphaned entries
delete
from addresses_version
where id in (select id from temp_address_ids_business_fk);

delete
from addresses
where id in (select id from temp_address_ids_business_fk);


-- verification i.e. cnt == 0
select count(1) as cnt
from addresses_version av
where id in (select id from temp_address_ids_business_fk);

select count(1) as cnt
from addresses a
where id in (select id from temp_address_ids_business_fk);


drop table temp_address_ids_business_fk;


-- ****************************************************************
-- addresses/addresses_history reference orphaned office entry
-- ****************************************************************

-- create temp table for address ids to delete
CREATE TEMP TABLE temp_address_ids_office_fk AS
select distinct a.id
from addresses a
         left join offices o on o.id = a.office_id
         left join addresses_version av on av.id = a.id
         left join parties pm on pm.mailing_address_id = a.id
         left join parties pd on pd.delivery_address_id = a.id
where (o.id is null and a.office_id is not null)
  and pm.id is null
  and pd.id is null;


-- backup data to be deleted
copy (
    select distinct av.*
    from addresses_version av
    where id in (select id from temp_address_ids_office_fk))
    TO '/tmp/16902_orphaned_data__addresses_version_fk_office.csv' WITH (FORMAT CSV, HEADER);

copy (
    select distinct a.*
    from addresses a
    where id in (select id from temp_address_ids_office_fk))
    TO '/tmp/16902_orphaned_data__addresses_fk_office.csv' WITH (FORMAT CSV, HEADER);


-- delete orphaned entries
delete
from addresses_version
where id in (select id from temp_address_ids_office_fk);

delete
from addresses
where id in (select id from temp_address_ids_office_fk);


-- verification i.e. cnt == 0
select count(1) as cnt
from addresses_version av
where id in (select id from temp_address_ids_office_fk);

select count(1) as cnt
from addresses a
where id in (select id from temp_address_ids_office_fk);

drop table temp_address_ids_office_fk;


-- ****************************************************************
-- parties_version reference orphaned delivery address entry
-- ****************************************************************

-- create temp table for parties ids to delete
CREATE TEMP TABLE temp_party_ids_delivery_addr AS
select distinct pv.id
from parties_version pv
         left join parties p on p.id = pv.id
         left join addresses a on a.id = pv.delivery_address_id
where pv.delivery_address_id is not null
  and a.id is null;


-- backup data to be deleted
copy (
    select distinct pv.*
    from parties_version pv
    where id in (select id from temp_party_ids_delivery_addr))
    TO '/tmp/16902_orphaned_data__parties_version_fk_delivery_addr.csv' WITH (FORMAT CSV, HEADER);

copy (
    select distinct p.*
    from parties p
    where id in (select id from temp_party_ids_delivery_addr))
    TO '/tmp/16902_orphaned_data__parties_fk_delivery_addr.csv' WITH (FORMAT CSV, HEADER);


-- delete orphaned entries
delete
from parties_version
where id in (select id from temp_party_ids_delivery_addr);

delete
from parties
where id in (select id from temp_party_ids_delivery_addr);


-- verification i.e. cnt == 0
select count(1) as cnt
from parties_version pv
where id in (select id from temp_party_ids_delivery_addr);

select count(1) as cnt
from parties p
where id in (select id from temp_party_ids_delivery_addr);

drop table temp_party_ids_delivery_addr;


-- ****************************************************************
-- parties_version reference orphaned mailing address entry
-- ****************************************************************


-- create temp table for parties ids to delete
CREATE TEMP TABLE temp_party_ids_mailing_addr AS
select distinct pv.id
from parties_version pv
         left join parties p on p.id = pv.id
         left join addresses a on a.id = pv.mailing_address_id
where pv.mailing_address_id is not null
  and a.id is null;


-- backup data to be deleted
copy (
    select distinct pv.*
    from parties_version pv
    where id in (select id from temp_party_ids_mailing_addr))
    TO '/tmp/16902_orphaned_data__parties_version_fk_mailing_addr.csv' WITH (FORMAT CSV, HEADER);

copy (
    select distinct p.*
    from parties p
    where id in (select id from temp_party_ids_mailing_addr))
    TO '/tmp/16902_orphaned_data__parties_fk_mailing_addr.csv' WITH (FORMAT CSV, HEADER);


-- delete orphaned entries
delete
from parties_version
where id in (select id from temp_party_ids_mailing_addr);

delete
from parties
where id in (select id from temp_party_ids_mailing_addr);


-- verification i.e. cnt == 0
select count(1) as cnt
from parties_version pv
where id in (select id from temp_party_ids_mailing_addr);

select count(1) as cnt
from parties p
where id in (select id from temp_party_ids_mailing_addr);

drop table temp_party_ids_mailing_addr;


-- ****************************************************************
-- party_roles_history reference orphaned filing entry
-- ****************************************************************

-- create temp table for party role ids to delete
CREATE TEMP TABLE temp_party_role_ids_filing_fk AS
select distinct prv.id
from party_roles_version prv
         left join filings f on prv.filing_id = f.id
where prv.filing_id is not null
  and f.id is null;


-- backup data to be deleted
copy (
    select distinct prv.*
    from party_roles_version prv
    where id in (select id from temp_party_role_ids_filing_fk))
    TO '/tmp/16902_orphaned_data__party_roles_version_fk_filing.csv' WITH (FORMAT CSV, HEADER);

copy (
    select distinct pr.*
    from party_roles pr
    where id in (select id from temp_party_role_ids_filing_fk))
    TO '/tmp/16902_orphaned_data__party_roles_fk_filing.csv' WITH (FORMAT CSV, HEADER);


-- delete orphaned entries
delete
from party_roles_version
where id in (select id from temp_party_role_ids_filing_fk);

delete
from party_roles
where id in (select id from temp_party_role_ids_filing_fk);


-- verification i.e. cnt == 0
select count(1) as cnt
from party_roles_version av
where id in (select id from temp_party_role_ids_filing_fk);

select count(1) as cnt
from party_roles a
where id in (select id from temp_party_role_ids_filing_fk);

drop table temp_party_role_ids_filing_fk;


-- ****************************************************************
-- party_roles_history reference orphaned business entry
-- ****************************************************************

-- create temp table for party role ids to delete
CREATE TEMP TABLE temp_party_role_ids_business_fk AS
select distinct prv.id
from party_roles_version prv
         left join businesses b on prv.business_id = b.id
where prv.business_id is not null
  and b.id is null;


-- backup data to be deleted
copy (
    select distinct prv.*
    from party_roles_version prv
    where id in (select id from temp_party_role_ids_business_fk))
    TO '/tmp/16902_orphaned_data__party_roles_version_fk_business.csv' WITH (FORMAT CSV, HEADER);

copy (
    select distinct pr.*
    from party_roles pr
    where id in (select id from temp_party_role_ids_business_fk))
    TO '/tmp/16902_orphaned_data__party_roles_fk_business.csv' WITH (FORMAT CSV, HEADER);


-- delete orphaned entries
delete
from party_roles_version
where id in (select id from temp_party_role_ids_business_fk);

delete
from party_roles
where id in (select id from temp_party_role_ids_business_fk);


-- verification i.e. cnt == 0
select count(1) as cnt
from party_roles_version av
where id in (select id from temp_party_role_ids_business_fk);

select count(1) as cnt
from party_roles a
where id in (select id from temp_party_role_ids_business_fk);

drop table temp_party_role_ids_business_fk;


-- ****************************************************************
-- party_roles_history reference orphaned party entry
-- ****************************************************************

-- create temp table for party role ids to delete
CREATE TEMP TABLE temp_party_role_ids_party_fk AS
select distinct prv.id
from party_roles_version prv
         left join party_roles pr on prv.id = pr.id
         left join parties p on prv.party_id = p.id
where prv.party_id is not null
  and p.id is null;


-- backup data to be deleted
copy (
    select distinct prv.*
    from party_roles_version prv
    where id in (select id from temp_party_role_ids_party_fk))
    TO '/tmp/16902_orphaned_data__party_roles_version_fk_party.csv' WITH (FORMAT CSV, HEADER);

copy (
    select distinct pr.*
    from party_roles pr
    where id in (select id from temp_party_role_ids_party_fk))
    TO '/tmp/16902_orphaned_data__party_roles_fk_party.csv' WITH (FORMAT CSV, HEADER);


-- delete orphaned entries
delete
from party_roles_version
where id in (select id from temp_party_role_ids_party_fk);

delete
from party_roles
where id in (select id from temp_party_role_ids_party_fk);


-- verification i.e. cnt == 0
select count(1) as cnt
from party_roles_version av
where id in (select id from temp_party_role_ids_party_fk);

select count(1) as cnt
from party_roles a
where id in (select id from temp_party_role_ids_party_fk);

drop table temp_party_role_ids_party_fk;


-- ****************************************************************
-- businesses_version entry referencing orphaned business entry
-- ****************************************************************

-- create temp table for business ids to delete
CREATE TEMP TABLE temp_business_ids AS
select distinct bv.id
from businesses_version bv
         left join businesses b on bv.id = b.id
where bv.id is not null
  and b.id is null;


-- backup data to be deleted
copy (
    select distinct bv.*
    from businesses_version bv
    where id in (select id from temp_business_ids))
    TO '/tmp/16902_orphaned_data__businesses_version.csv' WITH (FORMAT CSV, HEADER);

copy (
    select distinct b.*
    from businesses b
    where id in (select id from temp_business_ids))
    TO '/tmp/16902_orphaned_data__businesses.csv' WITH (FORMAT CSV, HEADER);


-- delete orphaned entries
delete
from businesses_version
where id in (select id from temp_business_ids);

delete
from businesses
where id in (select id from temp_business_ids);


-- verification i.e. cnt == 0
select count(1) as cnt
from businesses_version bv
where id in (select id from temp_business_ids);

select count(1) as cnt
from businesses b
where id in (select id from temp_business_ids);

drop table temp_business_ids;


-- ****************************************************************
-- orphaned state filings
-- ****************************************************************
UPDATE businesses_version bv
SET state_filing_id = NULL
FROM (SELECT bv.id, bv.identifier, bv.legal_type, bv.legal_name, bv.state_filing_id
      FROM businesses_version bv
               LEFT JOIN filings f ON bv.state_filing_id = f.id
      WHERE bv.state_filing_id IS NOT NULL
        AND f.id IS NULL) AS subquery
WHERE bv.id = subquery.id
  AND bv.identifier = subquery.identifier
  AND bv.legal_type = subquery.legal_type
  AND bv.legal_name = subquery.legal_name
  AND bv.state_filing_id = subquery.state_filing_id;