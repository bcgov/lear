-- Queries changed a bit as FF was enabled first and scripts will be run later

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

