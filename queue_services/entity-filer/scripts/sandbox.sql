-- AUTH DB Prod SQL
-- Run following sql against auth db in Prod to avoid collisions in sandbox.  Each time we grab the latest LEAR
-- dump from prod and obfuscate it, we will need to take account of the entity & affiliation entries previously created
-- in auth db.  To do this we will need to check what the latest business identifier was for business identifiers
-- prefixed with BC, C, CP and FM were and start the corresponding business identifier sequence in sandbox LEAR db
-- incremented by one

(SELECT
     'CP' as item_type,
     business_identifier,
     CAST(NULLIF(REGEXP_REPLACE(business_identifier, '^CP(\d+).*$', '\1'), '') AS INTEGER) + 1 as next_sequence_number
 FROM entities
 WHERE business_identifier LIKE 'CP%'
 ORDER BY CAST(NULLIF(REGEXP_REPLACE(business_identifier, '^CP(\d+).*$', '\1'), '') AS INTEGER) DESC NULLS LAST
 LIMIT 1)

UNION ALL

(SELECT
     'BC' as item_type,
     business_identifier,
     CAST(NULLIF(REGEXP_REPLACE(business_identifier, '^BC(\d+).*$', '\1'), '') AS INTEGER) + 1 as next_sequence_number
 FROM entities
 WHERE business_identifier LIKE 'BC%'
 ORDER BY CAST(NULLIF(REGEXP_REPLACE(business_identifier, '^BC(\d+).*$', '\1'), '') AS INTEGER) DESC NULLS LAST
 LIMIT 1)

UNION ALL

(SELECT
     'C' as item_type,
     business_identifier,
     CAST(NULLIF(REGEXP_REPLACE(business_identifier, '^C(\d+).*$', '\1'), '') AS INTEGER) + 1 as next_sequence_number
 FROM entities
 WHERE business_identifier LIKE 'C%'
   AND business_identifier NOT LIKE 'CP%'  -- Exclude CP identifiers
 ORDER BY CAST(NULLIF(REGEXP_REPLACE(business_identifier, '^C(\d+).*$', '\1'), '') AS INTEGER) DESC NULLS LAST
 LIMIT 1)

UNION ALL

(SELECT
     'FM' as item_type,
     business_identifier,
     CAST(NULLIF(REGEXP_REPLACE(business_identifier, '^FM(\d+).*$', '\1'), '') AS INTEGER) + 1 as next_sequence_number
 FROM entities
 WHERE business_identifier LIKE 'FM%'
 ORDER BY CAST(NULLIF(REGEXP_REPLACE(business_identifier, '^FM(\d+).*$', '\1'), '') AS INTEGER) DESC NULLS LAST
 LIMIT 1)

ORDER BY item_type;


-- LEAR DB Sandbox SQL
-- Run following SQL against LEAR DB sandbox once corresponding business identifier sequence start numbers have been
-- determined for business identifers prefixed with BC, C, CP and FM via auth queries in previous sql section

-- These sequences will not be available in PROD until COLIN shutdown
CREATE SEQUENCE business_identifier_c START <c_start_sequence_placeholder>;
CREATE SEQUENCE business_identifier_bc START <bc_start_sequence_placeholder>;

-- Update existing(SP/GP and Coops) business identifier sequences so they don't collide with prod.
-- Specifically, collisions are an issue with auth db "entities" table's business_identifier column as auth db is
-- using prod db for sandbox
ALTER SEQUENCE business_identifier_sp_gp RESTART WITH <fm_start_sequence_placeholder>;
ALTER SEQUENCE business_identifier_coop RESTART WITH <cp_start_sequence_placeholder>;


-- Verifying LEAR db sequence values
SELECT
    'business_identifier_c' AS sequence_name,
    last_value FROM business_identifier_c
UNION ALL
SELECT
    'business_identifier_bc',
    last_value FROM business_identifier_bc
UNION ALL
SELECT
    'business_identifier_sp_gp',
    last_value FROM business_identifier_sp_gp
UNION ALL
SELECT
    'business_identifier_coop',
    last_value FROM business_identifier_coop;


