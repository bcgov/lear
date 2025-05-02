-- Queries changed a bit as FF was enabled first and xcripts will be run later

-- query to get all ACTIVE businesses (BENs) for Corrections
select b.identifier, f.id, f.filing_date
from businesses b join filings f on b.id = f.business_id
where b.legal_type = 'BEN' and f.filing_type = 'incorporationApplication' and b.state = 'ACTIVE'
order by b.identifier asc;

-- query to get all ACTIVE businesses (BENs) which have "in progress" drafts
select distinct(b.identifier), f.id, f.filing_type
from businesses b join filings f on b.id = f.business_id
where b.legal_type = 'BEN' and b.state = 'ACTIVE' and f.status = 'DRAFT'
order by b.identifier asc;

-- query to get all businesses (BENs) for Registrar's Notation until 2/05/2025
select b.identifier, MIN(f.filing_date) AS ia_filing_date
from businesses b join filings f on b.id = f.business_id
where b.legal_type = 'BEN'
GROUP BY b.identifier
order by ia_filing_date desc;

-- query to get all businesses (BENs) for Corrections until 2/05/2025
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

