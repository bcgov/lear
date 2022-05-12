-- Description:
-- Update meta data for AR filings to include new annualReportFilingYear property so ledger filing display name for AR
-- filings can be displayed correctly.  Previously, the ledger display name logic for AR filings was using the
-- annualReportDate found in the filing meta_data field.  This worked for COLIN filings but not for LEAR COOP filings.
-- With LEAR COOP filings there is a scenario where the user can select an annual report date from the UI that results
-- in more than one LEAR AR filing with the same year for the annualReportDate property in the filing meta_data.
-- Scenarios involved:
--    1. COLIN AR filings have the correct year found in annualReportDate property of the filing meta data.
--       Add annualReportFilingYear property to filing.meta_data by extracting year from existing  annualReportDate
--       property found in the meta data for the COLIN AR filing.
--    2. LEAR AR filings can populate the new annualReportFilingYear property in the filing meta data by joining
--       against businesses_version table using the business id and transaction id.  The last_ar_year column value from
--       the matching businesses_version row can then be used for the new annualReportFilingYear property value in
--       the filing meta data.  Note: some LEAR AR filings json did have a ARFilingYear property that could be used
--       to determine the value for annualReportFilingYear but not all LEAR AR filings had this property.  As such,
--       we will just use the matching businesses_version table entries to populate the new annualReportFilingYear property
--       in the filing meta data.

-- start a transaction
begin;

-- scenario 1 (COLIN AR filings)
with t as (
    select f.id,
           f.business_id,
           f.source,
           EXTRACT(YEAR FROM
                   cast(f.meta_data -> 'annualReport' ->> 'annualReportDate' AS DATE)) AS annualReportFilingYear,
           f.meta_data                                                                 as md
    from filings f
    where f.source = 'COLIN'
      and f.filing_type = 'annualReport'
      and f.meta_data is not null
      and f.meta_data -> 'annualReport' -> 'annualReportFilingYear' is null
)
-- Add annualReportFilingYear to annualReport object of filing meta data
UPDATE filings f
SET meta_data=jsonb_insert(meta_data::jsonb, '{annualReport, annualReportFilingYear}',
                           cast('' || t.annualReportFilingYear || '' as jsonb))
    FROM t
WHERE f.id = t.id;

-- scenario 2 (LEAR AR filings)
with t as (
    select f.id,
           f.business_id,
           f.source,
           f.transaction_id,
           bv.last_ar_year as annualReportFilingYear,
           f.meta_data     as md
    from filings f
             join businesses_version bv ON f.business_id = bv.id AND f.transaction_id = bv.transaction_id
    where f.source = 'LEAR'
      and f.filing_type = 'annualReport'
      and f.meta_data is not null
      and f.meta_data -> 'annualReport' -> 'annualReportFilingYear' is null
)
-- Add annualReportFilingYear to annualReport object of filing meta data
UPDATE filings f
SET meta_data=jsonb_insert(meta_data::jsonb, '{annualReport, annualReportFilingYear}',
                           cast('' || t.annualReportFilingYear || '' as jsonb))
    FROM t
WHERE f.id = t.id;

-- Verify - all AR filings have annualReportFilingYear property in filing meta data
-- Expected value: 0
select count(f.*) as cnt
from filings f
where f.filing_type = 'annualReport'
  and f.meta_data is not null
  and f.meta_data -> 'annualReport' -> 'annualReportFilingYear' is null;


-- COMMIT OR ROLLBACK above updates after verification.  i.e. uncomment one of COMMIT or ROLLBACK commands below.

-- uncomment COMMIT; command on next line execute if commit transaction if all verification checks out
-- commit;

-- uncomment ROLLBACK; command on next line and execute to rollback transaction if verification doesn't checkout
-- rollback;
