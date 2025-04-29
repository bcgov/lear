-- query to get all businesses (BENs) for Registrar's Notation
select b.identifier
from businesses b
where b.legal_type = 'BEN'
order by b.identifier asc;

-- query to get all ACTIVE businesses (BENs) for Corrections
select b.identifier, f.id, f.effective_date
from businesses b join filings f on b.id = f.business_id
where b.legal_type = 'BEN' and f.filing_type = 'incorporationApplication' and b.state = 'ACTIVE'
order by f.effective_date desc;

-- query to get all ACTIVE businesses (BENs) which have "in progress" drafts
select b.identifier, f.id, f.filing_type
from businesses b join filings f on b.id = f.business_id
where b.legal_type = 'BEN' and b.state = 'ACTIVE' and f.status = 'DRAFT'
order by b.identifier asc;
