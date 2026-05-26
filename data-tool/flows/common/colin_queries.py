
from math import ceil
import re

from sqlalchemy import text

def build_corp_list(corp_list: str, chunksize: int) -> str:
    if not str(corp_list).strip():
        raise ValueError('empty corp_list')
    corp_nums = re.findall(r"'([^']*)'", corp_list)
    batch_size = min(chunksize, 999)
    num_batches = ceil(len(corp_nums) / batch_size)

    batch_ctes: list[str] = []
    batch_names: list[str] = []
    for idx in range(num_batches):
        batch = corp_nums[idx * batch_size: (idx +1)* batch_size]
        name = f'corp_list_{idx+1}'
        batch_names.append(name)
        args_sql = ",".join("'" + x.replace("'", "''") + "'" for x in batch)
        batch_ctes.append(
            f'{name} AS (SELECT column_value AS corp_num FROM TABLE(sys.odcivarchar2list({args_sql})))'
        )

    union_lines = [f' SELECT corp_num FROM {batch_names[0]}']
    union_lines.extend(f' UNION ALL SELECT corp_num FROM {name}' for name in batch_names[1:])
    corp_list_cte = 'corp_list AS (\n'+ '\n'.join(union_lines) + '\n)'
    return ',\n'.join([*batch_ctes, corp_list_cte])

def get_updated_identifiers(timestamp: str, corp_list: str, chunk_size: int) -> str:
    if not str(corp_list).strip():
        raise ValueError('empty corp_list')
    corp_list_ctes = build_corp_list(corp_list, chunk_size)
    query = f"""
    WITH {corp_list_ctes},
    latest_event AS (
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
        JOIN corp_list c
            ON c.corp_num = e.corp_num
        WHERE e.event_timestmp > TIMESTAMP '{timestamp}' - INTERVAL '2' HOUR
        AND NOT (
            EXISTS (
            SELECT 1
            FROM corporation c2
            WHERE c2.corp_num = e.corp_num
                AND c2.corp_frozen_typ_cd = 'C'
            )
            AND EXISTS (
            SELECT 1
            FROM corp_early_adopters cea
            WHERE cea.corp_num = e.corp_num
            )
        )
    ) SELECT le.EVENT_ID,
        le.corp_num,
        le.event_typ_cd,
        le.event_timestmp,
        le.trigger_dts,
        f.FILING_TYP_CD
    FROM latest_event le
    LEFT JOIN filing f on le.EVENT_ID = f.EVENT_ID
    WHERE rn = 1
    ORDER BY le.event_timestmp DESC, le.EVENT_ID DESC
    """
    return query

def get_identifiers_per_batch(mig_batch_id: int) -> str:
    return f"""
    SELECT string_agg(pg_catalog.quote_literal(trim(CAST(mcb.corp_num AS text))), ',') AS corp_list
    FROM mig_corp_batch mcb
    WHERE mcb.mig_batch_id = {mig_batch_id}
    """

def get_updated_identifiers_for_batch(timestamp: str, corp_list: str, chunk_size: int) -> str:
    """per batch get identifiers"""
    return get_updated_identifiers(timestamp, corp_list, 999)