def get_updated_identifiers(timestamp, corp_list):
    query = f"""
    SELECT e.event_id,
            e.corp_num,
            e.event_typ_cd,
            e.event_timestmp,
            e.trigger_dts,
            ROW_NUMBER() OVER (
            PARTITION BY e.corp_num
            ORDER BY e.event_timestmp DESC, e.event_id DESC
            ) AS rn
    FROM event e
    JOIN {corp_list} c
        ON c.corp_num = e.corp_num
    WHERE e.event_timestmp > TIMESTAMP '{timestamp}' -- reduce by 1 hour
    )
    SELECT le.EVENT_ID,
        le.corp_num,
        le.event_typ_cd,
        le.event_timestmp,
        le.trigger_dts,
        f.FILING_TYP_CD
    FROM latest_event le
    left join filing f on le.EVENT_ID = f.EVENT_ID
    WHERE rn = 1
    ORDER BY le.event_timestmp DESC, le.EVENT_ID DESC;
    """
    return query