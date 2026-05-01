
def get_updated_identifiers(timestamp, corp_list):
    if not str(corp_list).strip():
        raise ValueError('empty corp_list')
    
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
    JOIN (SELECT column_value AS corp_num
            FROM TABLE(sys.odcivarchar2list({corp_list})) c
        ON c.corp_num = e.corp_num
    WHERE e.event_timestmp > TIMESTAMP '{timestamp}' - INTERVAL '1' HOUR
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
    ORDER BY le.event_timestmp DESC, le.EVENT_ID DESC
    """
    return query

def get_identifiers_per_batch(mig_batch_id):
    query = f"""
    SELECT string_agg(qoute_literal(trim(mcb.corp_num:::text)), ',') AS corp_list
    FROM mig_corp_batch mcb
    WHERE mcb.mig_batch_id = {mig_batch_id}
    """
    return query

def get_updated_identifiers_for_batch(timestamp: str, mig_batch_id: int) -> str:
    """per batch get identifiers"""
    return get_updated_identifiers(timestamp, get_identifiers_per_batch(mig_batch_id))