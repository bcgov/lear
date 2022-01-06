-- Update for businesses where businesses.state is null to valid STATE for following scenarios:
--    1. businesses.dissolution_date is not null and dissolution filing json has dissolutionType of
--      'voluntary' or 'administrative'. Update businesses.state to 'HISTORICAL'
--    2. businesses.dissolution_date is not null and dissolution filing json is not proper.  One of the businesses
--          in PRD has a dissolution filing like this.  Update businesses.state to 'HISTORICAL'
--    3. businesses.dissolution_date is not null and obsolete filing type of 'voluntaryDissolution` is used.
--       Update businesses.state to 'HISTORICAL'
--    4. businesses.dissolution_date is null.  Update businesses.state to `ACTIVE'

-- scenario 1 (valid dissolution filing of sub type 'voluntary' or 'administrative')
update businesses
set state = 'HISTORICAL'
where id in (
    select b.id
    from filings f
             join businesses b ON f.business_id = b.id
    where f.filing_type = 'dissolution'
      and b.dissolution_date is not null
      and b.state is null
      and f.filing_json -> 'filing' -> 'dissolution' ->> 'dissolutionType' in ('voluntary', 'administrative')
    );

-- scenario 2 (dissolution filing json is incomplete but business has dissolution date)
update businesses
set state = 'HISTORICAL'
where id in (
    select b.id
    from filings f
             join businesses b ON f.business_id = b.id
    where f.filing_type = 'dissolution'
      and b.dissolution_date is not null
      and b.state is null
      and f.filing_json -> 'filing' -> 'dissolution' is null
);

-- scenario 3 (obsolete voluntaryDissolution filing type that was previously used)
update businesses
set state = 'HISTORICAL'
where id in (
    select b.id
    from filings f
             join businesses b ON f.business_id = b.id
    where f.filing_type = 'voluntaryDissolution'
      and b.dissolution_date is not null
      and b.state is null);

-- scenario 4 (business records that have not been dissolved)
update businesses
set state = 'ACTIVE'
where id in (
    select b.id
    from businesses b
    where b.state is null
      and b.dissolution_date is null);
