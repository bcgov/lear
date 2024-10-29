WITH related_tables AS (
    -- Get all tables that reference EVENT
    SELECT DISTINCT
        acc.table_name as referencing_table,
        acc.column_name as referencing_column
    FROM all_cons_columns acc
    JOIN all_constraints ac 
        ON acc.constraint_name = ac.constraint_name
    WHERE ac.r_constraint_name IN (
        SELECT constraint_name
        FROM all_constraints
        WHERE table_name = 'EVENT'  
            AND constraint_type IN ('P','F')
    )
),
nocdr_events AS (
    -- Get all EVENT_IDs from NOCDR filings
    SELECT EVENT_ID
    FROM FILING
    WHERE FILING_TYP_CD = 'NOCDR'  -- change the filing type as needed
)
SELECT 
    rt.referencing_table,
    rt.referencing_column,
    -- since read-only access to db, can't insert temp tables or create functions
    -- Add a note showing this is the query we need to run for each table, matching can be 0
    'SELECT COUNT(DISTINCT(' || rt.referencing_column || ')) FROM ' || rt.referencing_table || 
    ' WHERE ' || rt.referencing_column || ' IN (SELECT EVENT_ID FROM FILING WHERE FILING_TYP_CD = ''NOCDR'')' 
    as query_to_run
FROM related_tables rt
ORDER BY rt.referencing_table;
