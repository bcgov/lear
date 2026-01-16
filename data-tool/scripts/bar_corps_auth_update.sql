-- ******************************************************************************************
-- Script: BAR Business Auth Data Migration Update
-- Purpose: Updates auth database records for businesses that have filed Annual Reports
--          via the Business AR (BAR) process after migration from legacy (COLIN) to the
--          modernized system (LEAR).
--
-- What it does:
--   1. Entities Table: Ensures business_identifier has 'BC' prefix and sets is_loaded_lear = true
--   2. Entity Mapping Table: Inserts new mapping records with 'BC' prefixed identifiers
--
-- Usage:
--   - Replace placeholder identifiers (1111111, 2222222, etc.) with actual business numbers
--   - Run preview steps first to verify changes before committing
--   - Each section uses transactions with explicit COMMIT/ROLLBACK for safety
--
-- ******************************************************************************************

-- ------------------------------------------------------------------------------------------
-- Update Entities Table
-- ------------------------------------------------------------------------------------------
-- Step 1: Preview what will be updated (RUN THIS FIRST)
SELECT id,
       business_identifier AS current_identifier,
       CASE
           WHEN business_identifier LIKE 'BC%' THEN business_identifier
           ELSE 'BC' || business_identifier
           END             AS new_identifier,
       is_loaded_lear      AS current_flag,
       true                AS new_flag
FROM entities
WHERE regexp_replace(business_identifier, '^BC', '') IN (
                                                         '1111111', '2222222', '3333333'
    );

-- Step 2: If preview looks good, run the update in a transaction
BEGIN;

UPDATE entities
SET business_identifier = CASE
                              WHEN business_identifier LIKE 'BC%' THEN business_identifier
                              ELSE 'BC' || business_identifier
    END,
    is_loaded_lear      = true,
    modified            = CURRENT_TIMESTAMP
WHERE regexp_replace(business_identifier, '^BC', '') IN (
                                                         '1111111', '2222222', '3333333'
    )
  AND (
    -- Only update if changes are needed
    business_identifier NOT LIKE 'BC%'
        OR is_loaded_lear = false
        OR is_loaded_lear IS NULL
    );

-- Step 3: Verify the changes
SELECT id, business_identifier, is_loaded_lear, modified
FROM entities
WHERE business_identifier IN (
                              'BC1111111', 'BC2222222', 'BC3333333'
    );

-- Step 4: If everything looks correct, commit. Otherwise, rollback.
COMMIT;
-- ROLLBACK;  -- Use this instead if something looks wrong


-- ------------------------------------------------------------------------------------------
-- Update Entity Mapping Table
-- ------------------------------------------------------------------------------------------
-- Step 1: Preview what will be inserted (RUN THIS FIRST)
SELECT 'BC' || identifier AS business_identifier_to_insert,
       CASE
           WHEN EXISTS (SELECT 1
                        FROM entity_mapping em
                        WHERE em.business_identifier = 'BC' || identifier)
               THEN 'Already exists - will skip'
           ELSE 'Will be inserted'
           END            AS status
FROM unnest(ARRAY [
    '1111111', '2222222', '3333333'

    ]) AS identifier
ORDER BY identifier;

-- Step 2: If preview looks good, run the insert in a transaction
BEGIN;

INSERT INTO entity_mapping (business_identifier)
SELECT 'BC' || identifier
FROM unnest(ARRAY [
    '1111111', '2222222', '3333333'
    ]) AS identifier
WHERE NOT EXISTS (SELECT 1
                  FROM entity_mapping em
                  WHERE em.business_identifier = 'BC' || identifier);

-- Step 3: Verify the inserts
SELECT *
FROM entity_mapping
WHERE business_identifier IN (
                              'BC1111111', 'BC2222222', 'BC3333333'
    )
ORDER BY business_identifier;

-- Step 4: If everything looks correct, commit. Otherwise, rollback.
COMMIT;
-- ROLLBACK;  -- Use this instead if something looks wrong
