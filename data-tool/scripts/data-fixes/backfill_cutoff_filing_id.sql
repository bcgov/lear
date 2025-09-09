-- Description:
-- This script identifies the last historical filing before the 'lear_tombstone' filing for each business and sets 
-- backfill_cutoff_filing_id to that filing ID for businesses that have been ALREADY migrated.
--
-- Context:
-- During tombstone migration, historical filings from COLIN are migrated first, followed by a 'lear_tombstone' 
-- marker filing. The backfill_cutoff_filing_id should point to the last historical filing before this marker
-- to establish a clear boundary between migrated historical data and future LEAR-native filings.
--
-- What is exactly changing: Businesses that have been migrated (have a 'lear_tombstone' filing) but backfill_cutoff_filing_id is null

-- Update backfill_cutoff_filing_id for migrated businesses from null to the last historical filing <-- Main Query
WITH last_historical_filings AS (
    SELECT 
        b.id as business_id,
        f_tombstone.id as tombstone_filing_id,
        (
            SELECT MAX(f_inner.id) 
            FROM filings f_inner 
            WHERE f_inner.business_id = b.id 
                AND f_inner.id < f_tombstone.id
                AND f_inner.filing_type != 'lear_tombstone'
        ) as last_historical_filing_id
    FROM businesses b
        JOIN filings f_tombstone ON b.id = f_tombstone.business_id 
            AND f_tombstone.filing_type = 'lear_tombstone'
    WHERE 
        b.backfill_cutoff_filing_id IS NULL
)
UPDATE businesses 
SET backfill_cutoff_filing_id = lhf.last_historical_filing_id,
    last_modified = NOW()
FROM last_historical_filings lhf
WHERE businesses.id = lhf.business_id
    AND lhf.last_historical_filing_id IS NOT NULL;

-- The following queries are for verification purposes only

-- Show businesses that will be affected
SELECT
    b.id,
    b.identifier,
    b.legal_name,
    b.backfill_cutoff_filing_id as current_cutoff_id,
    f_tombstone.id as tombstone_filing_id,
    f_last.id as last_historical_filing_id,
    f_last.filing_type as last_filing_type,
    f_last.filing_date as last_filing_date
FROM businesses b
    -- Find the lear_tombstone filing for this business
    JOIN filings f_tombstone ON b.id = f_tombstone.business_id 
        AND f_tombstone.filing_type = 'lear_tombstone'
    -- Find the last filing before the tombstone (highest ID that's less than tombstone ID)
    JOIN filings f_last ON b.id = f_last.business_id 
        AND f_last.id = (
            SELECT MAX(f_inner.id) 
            FROM filings f_inner 
            WHERE f_inner.business_id = b.id 
                AND f_inner.id < f_tombstone.id
                AND f_inner.filing_type != 'lear_tombstone'
        )
WHERE 
    -- Only businesses that need backfilling
    b.backfill_cutoff_filing_id IS NULL
    -- Only migrated businesses (those with lear_tombstone)
    AND EXISTS (
        SELECT 1 FROM filings f 
        WHERE f.business_id = b.id 
            AND f.filing_type = 'lear_tombstone'
    )
ORDER BY b.identifier;

-- Count of businesses to be updated
SELECT COUNT(*) as businesses_to_update
FROM businesses b
WHERE b.backfill_cutoff_filing_id IS NULL
    AND EXISTS (
        SELECT 1 FROM filings f 
        WHERE f.business_id = b.id 
            AND f.filing_type = 'lear_tombstone'
    );

-- Check results after updating
SELECT 
    COUNT(*) as updated_businesses,
    COUNT(CASE WHEN b.backfill_cutoff_filing_id IS NOT NULL THEN 1 END) as businesses_with_cutoff_id,
    COUNT(CASE WHEN b.backfill_cutoff_filing_id IS NULL THEN 1 END) as businesses_without_cutoff_id
FROM businesses b
WHERE EXISTS (
    SELECT 1 FROM filings f 
    WHERE f.business_id = b.id 
        AND f.filing_type = 'lear_tombstone'
);

-- Show 10 updated records
SELECT 
    b.id,
    b.identifier,
    b.legal_name,
    b.backfill_cutoff_filing_id,
    f_cutoff.filing_type as cutoff_filing_type,
    f_cutoff.filing_date as cutoff_filing_date,
    f_tombstone.id as tombstone_filing_id
FROM businesses b
    LEFT JOIN filings f_cutoff ON b.backfill_cutoff_filing_id = f_cutoff.id
    JOIN filings f_tombstone ON b.id = f_tombstone.business_id 
        AND f_tombstone.filing_type = 'lear_tombstone'
WHERE b.backfill_cutoff_filing_id IS NOT NULL
ORDER BY b.identifier
LIMIT 10;

-- Edge case check: Businesses with lear_tombstone but no historical filings
-- These should have backfill_cutoff_filing_id remain NULL
-- This doesn't happen, but just in case
SELECT 
    b.id,
    b.identifier,
    b.legal_name,
    b.backfill_cutoff_filing_id,
    COUNT(f.id) as total_filings,
    COUNT(CASE WHEN f.filing_type = 'lear_tombstone' THEN 1 END) as tombstone_filings
FROM businesses b
    LEFT JOIN filings f ON b.id = f.business_id
WHERE EXISTS (
    SELECT 1 FROM filings f_tomb 
    WHERE f_tomb.business_id = b.id 
        AND f_tomb.filing_type = 'lear_tombstone'
)
GROUP BY b.id, b.identifier, b.legal_name, b.backfill_cutoff_filing_id
HAVING COUNT(f.id) = COUNT(CASE WHEN f.filing_type = 'lear_tombstone' THEN 1 END)
ORDER BY b.identifier;
