SET search_path TO TARGET_SCHEMA;

DROP TABLE IF EXISTS TARGET_SCHEMA.subset_validate_oracle_counts;
CREATE TABLE TARGET_SCHEMA.subset_validate_oracle_counts (
    corp_num        varchar(20) NOT NULL,
    table_name      varchar(20) NOT NULL,
    n               bigint NOT NULL,
    PRIMARY KEY (corp_num, table_name)
);

DROP TABLE IF EXISTS TARGET_SCHEMA.subset_validate_transfer_counts;
CREATE TABLE TARGET_SCHEMA.subset_validate_transfer_counts (
    corp_num        varchar(20) NOT NULL,
    table_name      varchar(20) NOT NULL,
    oracle_count    bigint NOT NULL,
    pg_count        bigint NOT NULL,
    delta           bigint NOT NULL,
    status          varchar(16) NOT NULL,
    PRIMARY KEY (corp_num, table_name)
);

-- pull per corp oracle count for refreshed candidate

transfer TARGET_SCHEMA.subset_validate_oracle_counts from cprd using
WITH corp_list AS (
    SELECT c.corp_num
    FROM corporation c 
    WHERE &oracle_corp_num_predicate
    AND &oracle_corp_type_predicate
    AND c.corp_num NOT IN ('0460007', '1255957', '1186381')
),
corps AS (
    SELECT c.corp_num AS. oracle_corp_num,
        CASE
            WHEN c.CORP_TYPE_CD IN ('BC', 'ULC', 'CC') THEN 'BC' || c.CORP_NUM 
            ELSE c.CORP_NUM
        END AS corp_num
    FROM corporation candidate
    JOIN corp_list cl ON cl.corp_num = c.corp_num
)
SELECT corp_num, table_name, n FROM (
    SELECT corp_num, 'corporation' AS table_name, COUNT(*) AS n 
    FROM corps
    GROUP BY corp_num
    
    UNION ALL
    SELECT c.corp_num, 'event', COUNT(*)
    FROM corps c
    JOIN event e ON e.corp_num = c.oracle_corp_num
    WHERE e.event_typ_cd NOT IN ('BNUPD', 'ADDLEDGR')
    GROUP BY c.corp_num

    UNION ALL
    SELECT c.corp_num, 'filing', COUNT(*)
    FROM corps c
    JOIN event e ON e.corp_num = c.oracle_corp_num
    JOIN filing f ON f.event_id = e.event_id
    GROUP BY c.corp_num

    UNION ALL
    SELECT c.corp_num, 'conv_event', COUNT(*)
    FROM corps c
    JOIN event e ON e.corp_num = c.oracle_corp_num
    JOIN CONV_EVENT ce ON ce.event_id = e.event_id
    GROUP BY c.corp_num

    UNION ALL
    SELECT c.corp_num, 'corp_restriction', COUNT(*)
    FROM corps c
    JOIN event e ON e.corp_num = c.oracle_corp_num
    JOIN CORP_RESTRICTION cr ON cr.event_id = e.event_id
    GROUP BY c.corp_num

    UNION ALL
    SELECT c.corp_num, 'share_struct_cls', COUNT(*)
    FROM corps c
    JOIN SHARE_STRUCT_CLS s ON s.corp_num = c.oracle_corp_num
    GROUP BY c.corp_num

    UNION ALL
    SELECT c.corp_num, 'share_series', COUNT(*)
    FROM corps c
    JOIN SHARE_SERIES s ON s.corp_num = c.oracle_corp_num
    GROUP BY c.corp_num
) counts;

-- comparison against extract for candidates

INSERT INTO TARGET_SCHEMA.subset_validate_transfer_counts
    (corp_num, table_name, oracle_count, pg_count, delta, status)
WITH corps AS (
    SELECT * FROM (
        VALUES &corp_ids_in
    ) AS t(corp_num)
),
tables AS (
    SELECT * FROM (
        VALUES 
        ('corporation'), ('event'), ('filing'), ('conv_event'), ('corp_restriction'),('share_struct_cls'), ('share_series')
    ) AS t(table_name)
),
pg_count AS (
    SELECT t.corp_num, 'corporation'::varchar AS table_name, COUNT(*)::bigint AS n 
    FROM TARGET_SCHEMA.corporation x
    JOIN corps t ON t.corp_num = x.corp_num
    GROUP BY t.corp_num

    UNION ALL
    SELECT t.corp_num, 'event', COUNT(*)
    FROM TARGET_SCHEMA.event x
    JOIN corps t ON t.corp_num = x.corp_num
    WHERE x.event_type_cd NOT IN ('BNUPD', 'ADDLEDGR')
    GROUP BY t.corp_num

    UNION ALL
    SELECT t.corp_num, 'filing', COUNT(*)
    FROM TARGET_SCHEMA.filing x
    JOIN TARGET_SCHEMA.event e ON e.event_id = x.event_id
    JOIN corps t ON t.corp_num = e.corp_num
    GROUP BY t.corp_num

    UNION ALL
    SELECT t.corp_num, 'conv_event', COUNT(*)
    FROM TARGET_SCHEMA.conv_event x
    JOIN TARGET_SCHEMA.event e ON e.event_id = x.event_id
    JOIN corps t ON t.corp_num = e.corp_num
    GROUP BY t.corp_num

    UNION ALL
    SELECT t.corp_num, 'corp_restriction', COUNT(*)
    FROM TARGET_SCHEMA.corp_restriction x
    JOIN corps t ON t.corp_num = x.corp_num
    GROUP BY t.corp_num

    UNION ALL
    SELECT t.corp_num, 'share_struct_cls', COUNT(*)
    FROM TARGET_SCHEMA.share_struct_cls x
    JOIN corps t ON t.corp_num = x.corp_num
    GROUP BY t.corp_num

    UNION ALL
    SELECT t.corp_num, 'share_series', COUNT(*)
    FROM TARGET_SCHEMA.share_series x
    JOIN corps t ON t.corp_num = x.corp_num
    GROUP BY t.corp_num
),
compared AS (
    SELECT
        c.corp_num,
        t.table_name,
        COALESCE(o.n, 0)::bigint AS oracle_count,
        COALESCE(p.n, 0)::bigint AS pg_count,
        (COALESCE(o.n, 0) - COALESCE(p.n, 0))::bigint AS delta,
        CASE    
            WHEN COALESCE(o.n, 0) = COALESCE(p.n, 0) THEN 'OK'
            ELSE 'MISMATCH'
        END AS status
    FROM corps c 
    CROSS JOIN tables t 
    LEFT JOIN TARGET_SCHEMA.subset_validate_oracle_counts o 
        ON o.corp_num = c.corp_num AND o.table_name = t.table_name
    LEFT JOIN pg_count p
        ON p.corp_num = c.corp_num AND p.table_name = t.table_name
)
SELECT corp_num, table_name, oracle_count, pg_count, delta, status
FROM compared;

-- summary
SELECT 
    table_name, SUM(oracle_count) AS oracle_total,
    SUM(pg_count) AS pg_total,
    SUM(delta) AS delta_total,
    SUM(CASE WHEN status = 'MISMATCH' THEN 1 ELSE 0 END) AS bad_corps
FROM TARGET_SCHEMA.subset_validate_transfer_counts
GROUP BY table_name
ORDER BY bad_corps DESC, table_name;

-- discrepency
SELECT corp_num, table_name, oracle_count, pg_count, delta, status
FROM TARGET_SCHEMA.subset_validate_transfer_counts
WHERE status = 'MISMATCH'
ORDER BY table_name, corp_num;

DROP TABLE IF EXISTS TARGET_SCHEMA.subset_validate_oracle_counts;