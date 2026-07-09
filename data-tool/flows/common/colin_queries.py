
from math import ceil
import re
from typing import Literal

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

def get_updated_identifiers(timestamp: str, corp_list: str, chunk_size: int, scope: Literal['batch', 'full']) -> str:
    corp_list_ctes = 'WITH '
    frozen_ctes = ''
    join_ctes = 'corporation'
    if scope == 'batch':
        join_ctes = 'corp_list'
        if not str(corp_list).strip():
            raise ValueError('empty corp_list')
        corp_list_ctes += build_corp_list(corp_list, chunk_size) + ',\n'
    if scope == 'full':
        frozen_ctes = frozen_cte() 
    query = f"""
    {corp_list_ctes}
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
        JOIN {join_ctes} c
            ON c.corp_num = e.corp_num
        WHERE e.event_timestmp > TIMESTAMP '{timestamp}' - INTERVAL '2' HOUR
        {frozen_ctes}
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

def get_identifiers_per_batch(mig_batch_id: int, target_schema: str) -> str:
    return f"""
    SELECT string_agg(pg_catalog.quote_literal(trim(CAST(mcb.corp_num AS text))), ',') AS corp_list
    FROM {target_schema}.mig_corp_batch mcb
    WHERE mcb.mig_batch_id IN ({mig_batch_id})
    """

def unfreeze_identifiers(target_schema: str) -> str:
    return f"""
    UPDATE {target_schema}.corporation AS c
    SET {target_schema}.corp_frozen_type_cd = NULL
    FROM {target_schema}.mig_group AS mg
            JOIN {target_schema}.mig_batch AS mb ON mb.mig_group_id = mg.id
            JOIN {target_schema}.mig_corp_batch AS mcb ON mcb.mig_batch_id = mb.id
    WHERE c.corp_num = mcb.corp_num
    -- cprd
    and mg.name in ('group_0', 'group_1', 'group_3', 'group_4','gcp_migration_group_test','misc_group')
    and mg.source_db = 'cprd'
    and mg.target_environment = 'prod'
    AND c.corp_frozen_type_cd IS NOT NULL;
    """

def frozen_cte() -> str:
    return f"""
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
    """

def get_updated_identifiers_for_batch(timestamp: str, corp_list: str, chunk_size: int, scope: str) -> str:
    """per batch get identifiers"""
    return get_updated_identifiers(timestamp, corp_list, chunk_size, scope)