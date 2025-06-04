-- Queries changed a bit as FF was enabled first and scripts will be run later

-- Incorporated as BEN (used this query to get all businesses (BENs with No In-progress DRAFTS) until 2025-05-02 3:16pm)
select 
    b.identifier, 
    b.state, 
    (select count(1) 
     from filings f2 
     where f2.business_id = b.id 
       and f2.status = 'DRAFT') <> 0 as has_draft_filings
from businesses b 
join filings f 
    on b.id = f.business_id
where
    b.legal_type = 'BEN' 
    and f.filing_type = 'incorporationApplication'
    and f.filing_date < TIMESTAMP '2025-05-02 15:16:00' AT TIME ZONE 'America/Los_Angeles'
    and b.identifier not in (
        select b1.identifier
        from public.filings f1
        join businesses b1 
            on b1.id = f1.business_id
        where
            f1.filing_type = 'alteration'
            and f1.meta_data->'alteration'->>'fromLegalType' in ('BC', 'ULC', 'CC', 'C', 'CUL', 'CCC')
            and f1.meta_data->'alteration'->>'toLegalType' in ('BEN', 'CBEN')
            and f1.filing_date < TIMESTAMP '2025-05-02 15:16:00' AT TIME ZONE 'America/Los_Angeles'
            and b1.legal_type = 'BEN'
    )
order by 
    b.state, 
    b.identifier;

-- Altered to BEN (used this query to get all businesses (BENs with No In-progress DRAFTS) until 2025-05-02 3:16pm)
select 
    b1.identifier, 
    b1.state, 
    (select count(1) 
     from filings f2 
     where f2.business_id = b1.id 
       and f2.status = 'DRAFT') <> 0 as has_draft_filings
from public.filings f1
join businesses b1 
    on b1.id = f1.business_id
where
    f1.filing_type = 'alteration'
    and f1.meta_data->'alteration'->>'fromLegalType' in ('BC', 'ULC', 'CC', 'C', 'CUL', 'CCC')
    and f1.meta_data->'alteration'->>'toLegalType' in ('BEN', 'CBEN')
    and f1.filing_date < TIMESTAMP '2025-05-02 15:16:00' AT TIME ZONE 'America/Los_Angeles'
    and b1.legal_type = 'BEN'
order by 
    b1.state, 
    b1.identifier;


-- query to get all businesses (BENs with No In-progress DRAFTS) for Registrar's Notation until 2025-05-02 3:16pm
select 
	b.identifier
from businesses b 
	 join filings f 
	 	on b.id = f.business_id
where
	b.legal_type = 'BEN' 
	and f.filing_type = 'incorporationApplication'
    and f.filing_date < TIMESTAMP '2025-05-02 15:16:00' AT TIME ZONE 'America/Los_Angeles'
	and (
		b.identifier NOT IN (
			select DISTINCT(bb.identifier) 
			from businesses bb
				join filings ff
					on bb.id = ff.business_id 
			where
				bb.legal_type = 'BEN'
				and ff.status = 'DRAFT'
		)
	)
order by
	b.identifier desc;

-- query to get ACTIVE businesses (BENs with No In-progress DRAFTS) for Corrections until 2025-05-02 3:16pm
select 
	b.identifier,
	f.id,
    f.filing_date
from businesses b 
	 join filings f 
	 	on b.id = f.business_id
where
	b.legal_type = 'BEN' 
	and f.filing_type = 'incorporationApplication'
    and f.filing_date < TIMESTAMP '2025-05-02 15:16:00' AT TIME ZONE 'America/Los_Angeles'
	and b.state = 'ACTIVE'
	and (
		b.identifier NOT IN (
			select DISTINCT(bb.identifier) 
			from businesses bb
				join filings ff
					on bb.id = ff.business_id 
			where
				bb.legal_type = 'BEN' 
				and bb.state = 'ACTIVE'
				and ff.status = 'DRAFT'
		)
	)
order by
	b.identifier desc;

