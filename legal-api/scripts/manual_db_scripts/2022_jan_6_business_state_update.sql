-- Description:
-- Update for businesses where businesses.state is null to valid STATE for following scenarios:
--    1. businesses.dissolution_date is not null and dissolution filing json has dissolutionType of
--      'voluntary' or 'administrative'. Update businesses.state to 'HISTORICAL'
--    2. businesses.dissolution_date is not null and dissolution filing json is not proper.  One of the businesses
--          in PRD has a dissolution filing like this.  Update businesses.state to 'HISTORICAL'
--    3. businesses.dissolution_date is not null and obsolete filing type of 'voluntaryDissolution` is used.
--       Update businesses.state to 'HISTORICAL'
--    4. businesses.dissolution_date is null.  Update businesses.state to `ACTIVE'

-- start a transaction
begin;

-- scenario 1 & 2
update businesses
set state = 'HISTORICAL'
where id in (
    select b.id
    from filings f
             join businesses b ON f.business_id = b.id
    where f.filing_type = 'dissolution'
      and b.dissolution_date is not null
      and b.state is null
      and (f.filing_json -> 'filing' -> 'dissolution' ->> 'dissolutionType' in ('voluntary', 'administrative')
        or f.filing_json -> 'filing' -> 'dissolution' is null)
);

-- verify scenario 1 & 2
select b.id, b.identifier, b.legal_name, b.state, b.dissolution_date
from filings f
         join businesses b ON f.business_id = b.id
where f.filing_type = 'dissolution'
  and b.dissolution_date is not null
  and b.state is not null
  and (f.filing_json -> 'filing' -> 'dissolution' ->> 'dissolutionType' in ('voluntary', 'administrative')
    or f.filing_json -> 'filing' -> 'dissolution' is null);

-- scenario 3
update businesses
set state = 'HISTORICAL'
where id in (
    select b.id
    from filings f
             join businesses b ON f.business_id = b.id
    where f.filing_type = 'voluntaryDissolution'
      and b.dissolution_date is not null
      and b.state is null);

-- verify scenario 3
select b.id, b.identifier, b.legal_name, b.state, b.dissolution_date
from filings f
         join businesses b ON f.business_id = b.id
where f.filing_type = 'voluntaryDissolution'
  and b.dissolution_date is not null
  and b.state is not null;

-- scenario 4
update businesses
set state = 'ACTIVE'
where id in (
    select b.id
    from businesses b
    where b.state is null
      and b.dissolution_date is null);

-- verify scenario 4
select b.id, b.identifier, b.legal_name, b.state, b.dissolution_date
from businesses b
where b.state is not null
  and b.dissolution_date is null;

-- COMMIT OR ROLLBACK above updates after verification.  i.e. uncomment one of COMMIT or ROLLBACK commands below.

-- uncomment COMMIT; command on next line execute if commit transaction if all verification checks out
-- commit;

-- uncomment ROLLBACK; command on next line and execute to rollback transaction if verification doesn't checkout
-- rollback;
