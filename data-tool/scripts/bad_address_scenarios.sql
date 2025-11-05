-- Bad Address Data: Example Extractors (Standalone Queries)
-- Purpose: Provide concrete example queries for business review of legacy address issues
-- Scope: Active/current office and party addresses (end_event_id IS NULL)
-- Notes for running and interpreting:
-- - Each query is standalone. Copy one block (from WITH/SELECT to the semicolon) and run it in pgAdmin.
-- - Address fields shown in samples: addr_line_1/2/3, city, province, country_typ_cd, postal_cd.
-- - "issue" explains the condition detected.
-- - Normalization uses simple regex tokenization (e.g., mapping British Columbia variations to 'bc').
-- - You can increase LIMIT values for larger extracts; beware of memory on large aggregations.
-- - Use: SET max_parallel_workers_per_gather = 0; SET enable_hashagg = off; if getting errors that no space left on device.

-- =====================================================================
-- Q1: City/Province likely in addr_line_2 (city is NULL) - clusters and counts
-- Purpose: Count common tokens in addr_line_2 when city is missing to identify likely city/province strings.
-- Input scope: Active office and party addresses only; addr_line_2 not empty; city is NULL/blank.
-- Detection logic: Normalize addr_line_2 by trimming, collapsing whitespace, lowercasing, and mapping 'british columbia' variants to 'bc'.
-- Outputs: normalized_value (token), count, sample_raw_values (top raw variants).
WITH address_usage AS (
    SELECT DISTINCT
        a.addr_id,
        'office'::text                AS address_kind,
        o.office_typ_cd               AS type_code,
        CASE WHEN o.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type,
        c.corp_num,
        c.corp_type_cd,
        cs.state_type_cd,
        cs.op_state_type_cd
    FROM address a
    JOIN office o       ON a.addr_id IN (o.mailing_addr_id, o.delivery_addr_id)
    JOIN event e        ON o.start_event_id = e.event_id
    JOIN corporation c  ON e.corp_num = c.corp_num
    LEFT JOIN corp_state cs ON cs.corp_num = c.corp_num AND cs.end_event_id IS NULL
    WHERE o.end_event_id IS NULL

    UNION ALL

    SELECT DISTINCT
        a.addr_id,
        'party'::text                 AS address_kind,
        cp.party_typ_cd               AS type_code,
        CASE WHEN cp.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type,
        c.corp_num,
        c.corp_type_cd,
        cs.state_type_cd,
        cs.op_state_type_cd
    FROM address a
    JOIN corp_party cp ON a.addr_id IN (cp.mailing_addr_id, cp.delivery_addr_id)
    JOIN event e       ON cp.start_event_id = e.event_id
    JOIN corporation c ON e.corp_num = c.corp_num
    LEFT JOIN corp_state cs ON cs.corp_num = c.corp_num AND cs.end_event_id IS NULL
    WHERE cp.end_event_id IS NULL
)
, line2_clusters AS (
    SELECT 
        au.addr_id,
        au.address_kind,
        au.type_code,
        au.address_type,
        au.corp_num,
        au.corp_type_cd,
        a.addr_line_2,
        a.city,
        a.province,
        a.country_typ_cd,
        a.postal_cd,
        lower(
          regexp_replace(
            regexp_replace(
              regexp_replace(coalesce(a.addr_line_2, ''), '[\.,]', ' ', 'g'),
              '\s+', ' ', 'g'
            ),
            '(british\s+columbia|b\s*\.?c\.?|b\.c\.)', 'bc', 'gi'
          )
        ) AS norm_line2
    FROM address_usage au
    JOIN address a ON a.addr_id = au.addr_id
    WHERE (a.city IS NULL OR btrim(a.city) = '')
      AND a.addr_line_2 IS NOT NULL AND btrim(a.addr_line_2) <> ''
)
SELECT 'Q1_top_line2_clusters' AS section,
       'Missing city; candidate values present in addr_line_2' AS issue,
       norm_line2              AS normalized_value,
       count(*)                AS count,
       (array_agg(DISTINCT addr_line_2 ORDER BY addr_line_2))[1:5] AS sample_raw_values
FROM line2_clusters
GROUP BY norm_line2
HAVING norm_line2 IS NOT NULL AND btrim(norm_line2) <> ''
ORDER BY count DESC
LIMIT 100;

-- =====================================================================
-- Q1a: Sample rows for a specific addr_line_2 cluster
-- How to use: Replace 'vancouver bc' with a value from Q1.normalized_value.
-- Purpose: Show concrete rows where city is missing but addr_line_2 contains a recognizable city/province candidate.
-- Outputs: Full address fields for business review.
WITH address_usage AS (
    SELECT DISTINCT
        a.addr_id,
        'office'::text                AS address_kind,
        o.office_typ_cd               AS type_code,
        CASE WHEN o.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type,
        c.corp_num,
        c.corp_type_cd
    FROM address a
    JOIN office o ON a.addr_id IN (o.mailing_addr_id, o.delivery_addr_id)
    JOIN event e  ON o.start_event_id = e.event_id
    JOIN corporation c ON e.corp_num = c.corp_num
    WHERE o.end_event_id IS NULL

    UNION ALL

    SELECT DISTINCT
        a.addr_id,
        'party'::text                 AS address_kind,
        cp.party_typ_cd               AS type_code,
        CASE WHEN cp.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type,
        c.corp_num,
        c.corp_type_cd
    FROM address a
    JOIN corp_party cp ON a.addr_id IN (cp.mailing_addr_id, cp.delivery_addr_id)
    JOIN event e  ON cp.start_event_id = e.event_id
    JOIN corporation c ON e.corp_num = c.corp_num
    WHERE cp.end_event_id IS NULL
)
, line2_clusters AS (
    SELECT 
        au.*, 
        a.addr_line_1,
        a.addr_line_2,
        a.addr_line_3,
        a.city,
        a.province,
        a.country_typ_cd,
        a.postal_cd,
        lower(
          regexp_replace(
            regexp_replace(
              regexp_replace(coalesce(a.addr_line_2, ''), '[\.,]', ' ', 'g'),
              '\s+', ' ', 'g'
            ),
            '(british\s+columbia|b\s*\.?c\.?|b\.c\.)', 'bc', 'gi'
          )
        ) AS target_norm
    FROM address_usage au
    JOIN address a ON a.addr_id = au.addr_id
    WHERE (a.city IS NULL OR btrim(a.city) = '')
      AND a.addr_line_2 IS NOT NULL AND btrim(a.addr_line_2) <> ''
)
SELECT 'Q1a_line2_cluster_samples' AS section,
       'Missing city; candidate values present in addr_line_2' AS issue,
       addr_id,
       corp_num,
       address_kind,
       type_code,
       address_type,
       addr_line_1,
       addr_line_2,
       addr_line_3,
       city,
       province,
       country_typ_cd,
       postal_cd
FROM line2_clusters
WHERE target_norm = 'vancouver bc'
ORDER BY addr_line_2
LIMIT 200;

-- =====================================================================
-- Q2: City/Province likely in addr_line_3 (city is NULL) - clusters and counts
-- Purpose: Same as Q1 but for addr_line_3. Outputs normalized_value, counts, sample variants.
WITH address_usage AS (
    SELECT DISTINCT
        a.addr_id,
        'office'::text AS address_kind,
        o.office_typ_cd AS type_code,
        CASE WHEN o.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN office o ON a.addr_id IN (o.mailing_addr_id, o.delivery_addr_id)
    WHERE o.end_event_id IS NULL

    UNION ALL

    SELECT DISTINCT
        a.addr_id,
        'party'::text AS address_kind,
        cp.party_typ_cd AS type_code,
        CASE WHEN cp.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN corp_party cp ON a.addr_id IN (cp.mailing_addr_id, cp.delivery_addr_id)
    WHERE cp.end_event_id IS NULL
)
, line3_clusters AS (
    SELECT 
        au.addr_id,
        a.addr_line_3,
        a.city,
        a.province,
        a.country_typ_cd,
        lower(
          regexp_replace(
            regexp_replace(
              regexp_replace(coalesce(a.addr_line_3, ''), '[\.,]', ' ', 'g'),
              '\s+', ' ', 'g'
            ),
            '(british\s+columbia|b\s*\.?c\.?|b\.c\.)', 'bc', 'gi'
          )
        ) AS norm_line3
    FROM address_usage au
    JOIN address a ON a.addr_id = au.addr_id
    WHERE (a.city IS NULL OR btrim(a.city) = '')
      AND a.addr_line_3 IS NOT NULL AND btrim(a.addr_line_3) <> ''
)
SELECT 'Q2_top_line3_clusters' AS section,
       'Missing city; candidate values present in addr_line_3' AS issue,
       norm_line3              AS normalized_value,
       count(*)                AS count,
       (array_agg(DISTINCT addr_line_3 ORDER BY addr_line_3))[1:5] AS sample_raw_values
FROM line3_clusters
GROUP BY norm_line3
HAVING norm_line3 IS NOT NULL AND btrim(norm_line3) <> ''
ORDER BY count DESC
LIMIT 100;

-- =====================================================================
-- Q2a: Sample rows for a specific addr_line_3 cluster
-- How to use: Replace 'vancouver bc' with a value from Q2.normalized_value.
-- Purpose: Concrete examples from addr_line_3 with full address fields for business review.
WITH address_usage AS (
    SELECT DISTINCT a.addr_id
    FROM address a
    JOIN office o ON a.addr_id IN (o.mailing_addr_id, o.delivery_addr_id)
    WHERE o.end_event_id IS NULL
    UNION ALL
    SELECT DISTINCT a.addr_id
    FROM address a
    JOIN corp_party cp ON a.addr_id IN (cp.mailing_addr_id, cp.delivery_addr_id)
    WHERE cp.end_event_id IS NULL
)
, line3_clusters AS (
    SELECT 
        a.addr_id,
        a.addr_line_1,
        a.addr_line_2,
        a.addr_line_3,
        a.city,
        a.province,
        a.country_typ_cd,
        a.postal_cd,
        lower(
          regexp_replace(
            regexp_replace(
              regexp_replace(coalesce(a.addr_line_3, ''), '[\.,]', ' ', 'g'),
              '\\s+', ' ', 'g'
            ),
            '(british\\s+columbia|b\\s*\\.?c\\.?|b\\.c\\.)', 'bc', 'gi'
          )
        ) AS target_norm
    FROM address a
    WHERE (a.city IS NULL OR btrim(a.city) = '')
      AND a.addr_line_3 IS NOT NULL AND btrim(a.addr_line_3) <> ''
)
SELECT 'Q2a_line3_cluster_samples' AS section,
       'Missing city; candidate values present in addr_line_3' AS issue,
       addr_id,
       addr_line_1,
       addr_line_2,
       addr_line_3,
       city,
       province,
       country_typ_cd,
       postal_cd
FROM line3_clusters
WHERE target_norm = 'vancouver bc'
ORDER BY addr_line_3
LIMIT 200;

-- =====================================================================
-- Q3: Province token only in addr_line_2 or addr_line_3 (city and province missing)
-- Purpose: Identify rows where province token appears in addr_line_2/3 while city AND province fields are both missing, signaling a misplacement.
-- Outputs: which_line shows whether the signal came from line2 or line3; counts per line.
WITH address_usage AS (
    SELECT DISTINCT
        a.addr_id,
        'office'::text AS address_kind,
        o.office_typ_cd AS type_code,
        CASE WHEN o.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN office o ON a.addr_id IN (o.mailing_addr_id, o.delivery_addr_id)
    WHERE o.end_event_id IS NULL

    UNION ALL

    SELECT DISTINCT
        a.addr_id,
        'party'::text AS address_kind,
        cp.party_typ_cd AS type_code,
        CASE WHEN cp.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN corp_party cp ON a.addr_id IN (cp.mailing_addr_id, cp.delivery_addr_id)
    WHERE cp.end_event_id IS NULL
)
, c AS (
  SELECT a.addr_id,
         au.address_kind,
         au.type_code,
         au.address_type,
         a.addr_line_2,
         a.addr_line_3
  FROM address_usage au
  JOIN address a ON a.addr_id = au.addr_id
  WHERE (a.city IS NULL OR btrim(a.city) = '')
    AND (a.province IS NULL OR btrim(a.province) = '')
)
SELECT 'Q3_province_only' AS section,
       'Province token present in addr_line_2/3; city and province missing' AS issue,
       CASE WHEN addr_line_2 ~* '\bbc\b|b\.c\.' THEN 'line2'
            WHEN addr_line_3 ~* '\bbc\b|b\.c\.' THEN 'line3'
       END AS which_line,
       count(*) AS count
FROM c
WHERE (
         addr_line_2 ~* '\bbc\b|b\.c\.'
         OR addr_line_3 ~* '\bbc\b|b\.c\.'
      )
GROUP BY which_line
ORDER BY count DESC;

-- =====================================================================
-- Q3a: Sample rows where province token present in addr_line_2/3 and city/province missing
-- Purpose: Show concrete examples with full address fields for business review.
WITH address_usage AS (
    SELECT DISTINCT a.addr_id
    FROM address a
    JOIN office o ON a.addr_id IN (o.mailing_addr_id, o.delivery_addr_id)
    WHERE o.end_event_id IS NULL
    UNION ALL
    SELECT DISTINCT a.addr_id
    FROM address a
    JOIN corp_party cp ON a.addr_id IN (cp.mailing_addr_id, cp.delivery_addr_id)
    WHERE cp.end_event_id IS NULL
)
SELECT 'Q3a_province_token_samples' AS section,
       'Province token present in addr_line_2/3; city and province missing' AS issue,
       a.addr_id,
       a.addr_line_1,
       a.addr_line_2,
       a.addr_line_3,
       a.city,
       a.province,
       a.country_typ_cd,
       a.postal_cd
FROM address a
JOIN address_usage au ON au.addr_id = a.addr_id
WHERE (a.city IS NULL OR btrim(a.city) = '')
  AND (a.province IS NULL OR btrim(a.province) = '')
  AND (a.addr_line_2 ~* '\bbc\b|b\.c\.' OR a.addr_line_3 ~* '\bbc\b|b\.c\.')
LIMIT 200;

-- =====================================================================
-- Q4: City and province present but country missing (examples)
-- Purpose: Where both city and province are filled but country is blank for business review.
WITH address_usage AS (
    SELECT DISTINCT
        a.addr_id,
        'office'::text AS address_kind,
        o.office_typ_cd AS type_code,
        CASE WHEN o.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN office o ON a.addr_id IN (o.mailing_addr_id, o.delivery_addr_id)
    WHERE o.end_event_id IS NULL

    UNION ALL

    SELECT DISTINCT
        a.addr_id,
        'party'::text AS address_kind,
        cp.party_typ_cd AS type_code,
        CASE WHEN cp.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN corp_party cp ON a.addr_id IN (cp.mailing_addr_id, cp.delivery_addr_id)
    WHERE cp.end_event_id IS NULL
)
SELECT 'Q4_city_province_without_country' AS section,
       'City and province present; country missing' AS issue,
       au.address_kind,
       au.type_code,
       au.address_type,
       a.addr_id,
       a.addr_line_1,
       a.addr_line_2,
       a.addr_line_3,
       a.city,
       a.province,
       a.country_typ_cd,
       a.postal_cd
FROM address_usage au
JOIN address a ON a.addr_id = au.addr_id
WHERE (a.city IS NOT NULL AND btrim(a.city) <> '')
  AND (a.province IS NOT NULL AND btrim(a.province) <> '')
  AND (a.country_typ_cd IS NULL OR btrim(a.country_typ_cd) = '')
ORDER BY a.province NULLS LAST, au.address_kind, au.type_code
LIMIT 200;

-- =====================================================================
-- Q5: Missing City & Country & Postal (worst-case) - examples
-- Purpose: Rows with minimal information (city/country/postal all missing) to triage and determine approach.
WITH address_usage AS (
    SELECT DISTINCT
        a.addr_id,
        'office'::text AS address_kind,
        o.office_typ_cd AS type_code,
        CASE WHEN o.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN office o ON a.addr_id IN (o.mailing_addr_id, o.delivery_addr_id)
    WHERE o.end_event_id IS NULL

    UNION ALL

    SELECT DISTINCT
        a.addr_id,
        'party'::text AS address_kind,
        cp.party_typ_cd AS type_code,
        CASE WHEN cp.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN corp_party cp ON a.addr_id IN (cp.mailing_addr_id, cp.delivery_addr_id)
    WHERE cp.end_event_id IS NULL
)
SELECT 'Q5_missing_city_country_postal' AS section,
       'Missing city, country, and postal' AS issue,
       au.address_kind,
       au.type_code,
       au.address_type,
       a.addr_id,
       a.addr_line_1,
       a.addr_line_2,
       a.addr_line_3,
       a.city,
       a.province,
       a.country_typ_cd,
       a.postal_cd
FROM address_usage au
JOIN address a ON a.addr_id = au.addr_id
WHERE (a.city IS NULL OR btrim(a.city) = '')
  AND (a.country_typ_cd IS NULL OR btrim(a.country_typ_cd) = '')
  AND (a.postal_cd IS NULL OR btrim(a.postal_cd) = '')
LIMIT 200;

-- =====================================================================
-- Q6: All key fields empty (addr_line_1, city, postal)
-- Purpose: Addresses missing all three key fields (addr_line_1, city, postal) to identify unusable records.
WITH address_usage AS (
    SELECT DISTINCT
        a.addr_id,
        'office'::text AS address_kind,
        o.office_typ_cd AS type_code,
        CASE WHEN o.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN office o ON a.addr_id IN (o.mailing_addr_id, o.delivery_addr_id)
    WHERE o.end_event_id IS NULL

    UNION ALL

    SELECT DISTINCT
        a.addr_id,
        'party'::text AS address_kind,
        cp.party_typ_cd AS type_code,
        CASE WHEN cp.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN corp_party cp ON a.addr_id IN (cp.mailing_addr_id, cp.delivery_addr_id)
    WHERE cp.end_event_id IS NULL
)
SELECT 'Q6_all_fields_empty' AS section,
       'Key fields empty: addr_line_1, city, postal' AS issue,
       au.address_kind,
       au.type_code,
       au.address_type,
       a.addr_id,
       a.addr_line_1,
       a.addr_line_2,
       a.addr_line_3,
       a.city,
       a.province,
       a.country_typ_cd,
       a.postal_cd
FROM address_usage au
JOIN address a ON a.addr_id = au.addr_id
WHERE (a.addr_line_1 IS NULL OR btrim(a.addr_line_1) = '')
  AND (a.city IS NULL OR btrim(a.city) = '')
  AND (a.postal_cd IS NULL OR btrim(a.postal_cd) = '')
LIMIT 200;

-- =====================================================================
-- Q7: Multi-field compressed into addr_line_1 (detect CA postal or province token in line1)
-- Purpose: Identify addr_line_1 that appears to contain multiple elements (e.g., a CA postal or 'BC' token) while city/province missing.
WITH address_usage AS (
    SELECT DISTINCT
        a.addr_id,
        'office'::text AS address_kind,
        o.office_typ_cd AS type_code,
        CASE WHEN o.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN office o ON a.addr_id IN (o.mailing_addr_id, o.delivery_addr_id)
    WHERE o.end_event_id IS NULL

    UNION ALL

    SELECT DISTINCT
        a.addr_id,
        'party'::text AS address_kind,
        cp.party_typ_cd AS type_code,
        CASE WHEN cp.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN corp_party cp ON a.addr_id IN (cp.mailing_addr_id, cp.delivery_addr_id)
    WHERE cp.end_event_id IS NULL
)
SELECT 'Q7_multifield_in_line1' AS section,
       'Possible multi-field in addr_line_1; city/province missing' AS issue,
       au.address_kind,
       au.type_code,
       au.address_type,
       a.addr_id,
       a.addr_line_1,
       a.addr_line_2,
       a.addr_line_3,
       a.city,
       a.province,
       a.country_typ_cd,
       a.postal_cd
FROM address_usage au
JOIN address a ON a.addr_id = au.addr_id
WHERE (
         a.addr_line_1 ~* '[A-Za-z][0-9][A-Za-z]\s?[0-9][A-Za-z][0-9]'
      OR a.addr_line_1 ~* '\\bbc\\b|b\\.c\\.|british\\s+columbia'
      )
  AND (a.city IS NULL OR btrim(a.city) = '' OR a.province IS NULL OR btrim(a.province) = '')
LIMIT 200;

-- =====================================================================
-- Q8: City present but province missing (and postal looks CA)
-- Purpose: Where city exists and postal looks CA, but province is empty; suggests country='CA' for consideration.
WITH address_usage AS (
    SELECT DISTINCT
        a.addr_id,
        'office'::text AS address_kind,
        o.office_typ_cd AS type_code,
        CASE WHEN o.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN office o ON a.addr_id IN (o.mailing_addr_id, o.delivery_addr_id)
    WHERE o.end_event_id IS NULL

    UNION ALL

    SELECT DISTINCT
        a.addr_id,
        'party'::text AS address_kind,
        cp.party_typ_cd AS type_code,
        CASE WHEN cp.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN corp_party cp ON a.addr_id IN (cp.mailing_addr_id, cp.delivery_addr_id)
    WHERE cp.end_event_id IS NULL
)
SELECT 'Q8_city_present_missing_province' AS section,
       'City present; province missing; CA-format postal present' AS issue,
       au.address_kind,
       au.type_code,
       au.address_type,
       a.addr_id,
       a.addr_line_1,
       a.addr_line_2,
       a.addr_line_3,
       a.city,
       a.province,
       a.country_typ_cd,
       a.postal_cd
FROM address_usage au
JOIN address a ON a.addr_id = au.addr_id
WHERE (a.city IS NOT NULL AND btrim(a.city) <> '')
  AND (a.province IS NULL OR btrim(a.province) = '')
  AND (a.postal_cd ~* '^[A-Za-z][0-9][A-Za-z]\s?[0-9][A-Za-z][0-9]$')
LIMIT 200;

-- =====================================================================
-- Q9: Province present but city missing
-- Purpose: Where province exists but city is empty; inverse of Q8. Might need manual review or city inference.
WITH address_usage AS (
    SELECT DISTINCT
        a.addr_id,
        'office'::text AS address_kind,
        o.office_typ_cd AS type_code,
        CASE WHEN o.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN office o ON a.addr_id IN (o.mailing_addr_id, o.delivery_addr_id)
    WHERE o.end_event_id IS NULL

    UNION ALL

    SELECT DISTINCT
        a.addr_id,
        'party'::text AS address_kind,
        cp.party_typ_cd AS type_code,
        CASE WHEN cp.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN corp_party cp ON a.addr_id IN (cp.mailing_addr_id, cp.delivery_addr_id)
    WHERE cp.end_event_id IS NULL
)
SELECT 'Q9_province_present_city_missing' AS section,
       'Province present; city missing' AS issue,
       au.address_kind,
       au.type_code,
       au.address_type,
       a.addr_id,
       a.addr_line_1,
       a.addr_line_2,
       a.addr_line_3,
       a.city,
       a.province,
       a.country_typ_cd,
       a.postal_cd
FROM address_usage au
JOIN address a ON a.addr_id = au.addr_id
WHERE (a.province IS NOT NULL AND btrim(a.province) <> '')
  AND (a.city IS NULL OR btrim(a.city) = '')
ORDER BY a.province NULLS LAST, au.address_kind, au.type_code
LIMIT 200;

-- =====================================================================
-- Q10: Postal code present but city and country both missing
-- Purpose: Where postal code exists but no geographic context (city/country). Postal might be parseable to infer location.
WITH address_usage AS (
    SELECT DISTINCT
        a.addr_id,
        'office'::text AS address_kind,
        o.office_typ_cd AS type_code,
        CASE WHEN o.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN office o ON a.addr_id IN (o.mailing_addr_id, o.delivery_addr_id)
    WHERE o.end_event_id IS NULL

    UNION ALL

    SELECT DISTINCT
        a.addr_id,
        'party'::text AS address_kind,
        cp.party_typ_cd AS type_code,
        CASE WHEN cp.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN corp_party cp ON a.addr_id IN (cp.mailing_addr_id, cp.delivery_addr_id)
    WHERE cp.end_event_id IS NULL
)
SELECT 'Q10_postal_without_city_country' AS section,
       'Postal code present; city and country missing' AS issue,
       au.address_kind,
       au.type_code,
       au.address_type,
       a.addr_id,
       a.addr_line_1,
       a.addr_line_2,
       a.addr_line_3,
       a.city,
       a.province,
       a.country_typ_cd,
       a.postal_cd
FROM address_usage au
JOIN address a ON a.addr_id = au.addr_id
WHERE (a.postal_cd IS NOT NULL AND btrim(a.postal_cd) <> '')
  AND (a.city IS NULL OR btrim(a.city) = '')
  AND (a.country_typ_cd IS NULL OR btrim(a.country_typ_cd) = '')
ORDER BY a.postal_cd, au.address_kind, au.type_code
LIMIT 200;

-- =====================================================================
-- Q11: Province code in city field
-- Purpose: Data in wrong field. Check if city contains typical province codes which suggests misplacement.
WITH address_usage AS (
    SELECT DISTINCT
        a.addr_id,
        'office'::text AS address_kind,
        o.office_typ_cd AS type_code,
        CASE WHEN o.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN office o ON a.addr_id IN (o.mailing_addr_id, o.delivery_addr_id)
    WHERE o.end_event_id IS NULL

    UNION ALL

    SELECT DISTINCT
        a.addr_id,
        'party'::text AS address_kind,
        cp.party_typ_cd AS type_code,
        CASE WHEN cp.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN corp_party cp ON a.addr_id IN (cp.mailing_addr_id, cp.delivery_addr_id)
    WHERE cp.end_event_id IS NULL
)
SELECT 'Q11_province_code_in_city' AS section,
       'Province code appears in city field; possible misplacement' AS issue,
       au.address_kind,
       au.type_code,
       au.address_type,
       a.addr_id,
       a.addr_line_1,
       a.addr_line_2,
       a.addr_line_3,
       a.city,
       a.province,
       a.country_typ_cd,
       a.postal_cd
FROM address_usage au
JOIN address a ON a.addr_id = au.addr_id
WHERE (a.city IS NOT NULL AND btrim(a.city) <> '')
  AND (
       a.city ~* '^\s*(BC|AB|SK|MB|ON|QC|NB|NS|PE|NL|YT|NT|NU)\s*$'
       OR a.city ~* '^\s*(B\.C\.|BRITISH COLUMBIA)\s*$'
      )
ORDER BY a.city, au.address_kind, au.type_code
LIMIT 200;

-- =====================================================================
-- Q12: Duplicate city in multiple fields
-- Purpose: Same city name appears in both city field and addr_line_2/3, suggesting redundant data that could be cleaned.
WITH address_usage AS (
    SELECT DISTINCT
        a.addr_id,
        'office'::text AS address_kind,
        o.office_typ_cd AS type_code,
        CASE WHEN o.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN office o ON a.addr_id IN (o.mailing_addr_id, o.delivery_addr_id)
    WHERE o.end_event_id IS NULL

    UNION ALL

    SELECT DISTINCT
        a.addr_id,
        'party'::text AS address_kind,
        cp.party_typ_cd AS type_code,
        CASE WHEN cp.mailing_addr_id = a.addr_id THEN 'mailing' ELSE 'delivery' END AS address_type
    FROM address a
    JOIN corp_party cp ON a.addr_id IN (cp.mailing_addr_id, cp.delivery_addr_id)
    WHERE cp.end_event_id IS NULL
)
SELECT 'Q12_duplicate_city_in_fields' AS section,
       'City appears in both city field and addr_line_2 or addr_line_3; redundant data' AS issue,
       au.address_kind,
       au.type_code,
       au.address_type,
       a.addr_id,
       a.addr_line_1,
       a.addr_line_2,
       a.addr_line_3,
       a.city,
       a.province,
       a.country_typ_cd,
       a.postal_cd
FROM address_usage au
JOIN address a ON a.addr_id = au.addr_id
WHERE (a.city IS NOT NULL AND btrim(a.city) <> '')
  AND (
       (a.addr_line_2 IS NOT NULL AND lower(btrim(a.addr_line_2)) = lower(btrim(a.city)))
       OR (a.addr_line_3 IS NOT NULL AND lower(btrim(a.addr_line_3)) = lower(btrim(a.city)))
       OR (a.addr_line_2 ~* ('(^|[^a-zA-Z])' || regexp_replace(btrim(a.city), '([.*+?^${}()|[\]\\])', '\\\1', 'g') || '([^a-zA-Z]|$)'))
       OR (a.addr_line_3 ~* ('(^|[^a-zA-Z])' || regexp_replace(btrim(a.city), '([.*+?^${}()|[\]\\])', '\\\1', 'g') || '([^a-zA-Z]|$)'))
      )
ORDER BY a.city, au.address_kind, au.type_code
LIMIT 200;
