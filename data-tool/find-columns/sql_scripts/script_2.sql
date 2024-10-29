SELECT * 
FROM TABLE_NAME t -- change the table name as needed
WHERE t.EVENT_ID_COLUMN IN ( -- change the event_id_column name as needed
	SELECT e.EVENT_ID 
	FROM EVENT e 
	JOIN FILING f ON e.EVENT_ID = f.EVENT_ID 
	WHERE f.FILING_TYP_CD = 'NOCDR' -- change filing type as needed
)
FETCH FIRST 100 ROWS ONLY; -- change to the limits you want
