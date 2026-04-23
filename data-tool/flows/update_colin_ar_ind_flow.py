from typing import List

from prefect import flow, task
from prefect.cache_policies import NO_CACHE
from sqlalchemy import Engine, text

from common.init_utils import colin_extract_init, colin_oracle_init, get_config

MIG_CORP_FILTER_BASE = """
    SELECT DISTINCT mcb.corp_num
    FROM mig_corp_batch mcb
    JOIN mig_batch b ON b.id = mcb.mig_batch_id
    JOIN mig_group g ON g.id = b.mig_group_id
    WHERE 1 = 1
"""

UPDATE_AR_IND_QUERY = """
    UPDATE corporation c
    SET c.SEND_AR_IND = 'N'
    WHERE c.corp_num IN ({corps})
"""

def parse_csv(csv_val: str) -> List[int]:
    if not csv_val:
        return []
    return [int(token.strip()) for token in csv_val.split(',') if token.strip().isdigit()]

@task(cache_policy=NO_CACHE)
def get_candidates(config, colin_engine: Engine) -> List[str]:
    if not config.USE_MIGRATION_FILTER:
        return []

    batch_ids = parse_csv(config.MIG_BATCH_IDS or "")
    group_ids = parse_csv(config.MIG_GROUP_IDS or "")

    sql_parts = [MIG_CORP_FILTER_BASE]
    params = {}
    if batch_ids:
        sql_parts.append("AND b.id = ANY(:batch_ids)")
        params['batch_ids'] = batch_ids
    if group_ids:
        sql_parts.append("AND g.id = ANY(:group_ids)")
        params['group_ids'] = group_ids

    sql = " ".join(sql_parts)

    with colin_engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()
        candidates = [row[0] for row in rows]
        print(f'👷 MIG corp candidates found: {len(candidates)}')

        # Strip "BC" prefix if present
        colin_identifiers = [corp[2:] if corp.startswith("BC") else corp for corp in candidates]
        return colin_identifiers

def chunk_list(data: List[str], size: int = 1000):
    # chunk size is set to 1000 to avoid hitting limit on oracle database
    for i in range(0, len(data), size):
        yield data[i:i + size]

@task(retries=2, retry_delay_seconds=5)
def update_chunk(ids_chunk: List[str]) -> int:
    corps_str = ",".join(f"'{corp}'" for corp in ids_chunk)
    sql = UPDATE_AR_IND_QUERY.format(corps=corps_str)

    with colin_oracle_init(get_config()).connect() as conn:
        result = conn.execute(text(sql))
        conn.commit()
        return result.rowcount

@flow(name='Update-Colin-AR-Indicator-Flow', log_prints=True)
def update_colin_ar_ind_flow():
    config = get_config()
    colin_extract_engine = colin_extract_init(config)

    candidates = get_candidates(config, colin_extract_engine)
    print(f'👷 Using MIG filter mode with {len(candidates)} candidates')

    total_updated = 0
    for chunk in chunk_list(candidates, 1000):
        print(f"Processing chunk of {len(chunk)} records")
        updated = update_chunk(chunk)
        total_updated += updated

    print(f"Total records updated: {total_updated}")

if __name__ == '__main__':
    update_colin_ar_ind_flow()