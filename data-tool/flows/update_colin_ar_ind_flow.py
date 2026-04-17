from typing import List

from prefect import flow, task
from prefect.cache_policies import NO_CACHE
from sqlalchemy import Engine, bindparam, text

from common.init_utils import colin_extract_init, colin_oracle_init, get_config

# --- MIG corp selection (from COLIN) used when USE_MIGRATION_FILTER = True ---
MIG_CORP_FILTER_BASE = """
    SELECT DISTINCT mcb.corp_num
    FROM mig_corp_batch mcb
    JOIN mig_batch b  ON b.id = mcb.mig_batch_id
    JOIN mig_group g  ON g.id = b.mig_group_id
    WHERE 1 = 1
    {batch_filter}
    {group_filter}
"""

colin_update_ar_ind_query = """
    UPDATE corporation c
    SET c.SEND_AR_IND = 'Y'
    WHERE c.corp_num IN ({corps})
"""

def _parse_csv(csv_val: str) -> List[int]:
    if not csv_val:
        return []

    return [
        int(token)
        for token in (t.strip() for t in csv_val.split(','))
        if token.isdigit()
    ]


@task(cache_policy=NO_CACHE)
def get_candidates(config, colin_engine: Engine) -> List[str]:
    """
    Build the candidate corp list purely from MIG metadata (COLIN).
    This is used to *replace* suffix-based selection when USE_MIGRATION_FILTER is True.
    """
    if not config.USE_MIGRATION_FILTER:
        return []

    # Parse CSV env strings into integer lists for expanding binds
    batch_ids = _parse_csv(config.MIG_BATCH_IDS) if config.MIG_BATCH_IDS else []
    group_ids = _parse_csv(config.MIG_GROUP_IDS) if config.MIG_GROUP_IDS else []

    batch_filter = "AND b.id IN :batch_ids" if batch_ids else ""
    group_filter = "AND g.id IN :group_ids" if group_ids else ""
    sql = MIG_CORP_FILTER_BASE.format(batch_filter=batch_filter, group_filter=group_filter)

    # Conditionally bind lists with expanding (environment not used by this query)
    stmt = text(sql)
    params = {}

    if batch_ids:
        stmt = stmt.bindparams(bindparam('batch_ids', expanding=True))
        params['batch_ids'] = batch_ids
    if group_ids:
        stmt = stmt.bindparams(bindparam('group_ids', expanding=True))
        params['group_ids'] = group_ids

    with colin_engine.connect() as conn:
        rows = conn.execute(stmt, params).fetchall()
        candidates = [r[0] for r in rows]
        print(f'👷 MIG corp candidates found: {len(candidates)}')
        cleaned = [
            ",".join(item[2:] if item.startswith("BC") else item for item in row.split(","))
            for row in candidates
        ]
        return cleaned


# --- HELPER: CHUNK LIST ---
def chunk_list(data, size=1000):
    for i in range(0, len(data), size):
        yield data[i:i + size]

# --- TASK: UPDATE ONE CHUNK ---
@task(retries=2, retry_delay_seconds=5)
def update_chunk(ids_chunk):
    corps_str = ",".join(f"'{corp}'" for corp in ids_chunk)
    sql = colin_update_ar_ind_query.format(corps=corps_str)

    with colin_oracle_init(get_config()).connect() as conn:
        result = conn.execute(text(sql))
        conn.commit()
        return result.rowcount

@flow(
    name='Update-Colin-AR-Indicator-Flow',
    log_prints=True,
)
def update_colin_ar_ind_flow():
    try:
        config = get_config()
        colin_extract_engine = colin_extract_init(config)

        # Get candidates
        candidates = get_candidates(config, colin_extract_engine)
        print(f'👷 Using MIG filter mode with {len(candidates)} candidates')

        total_updated = 0

        for chunk in chunk_list(candidates, 1000):
            print(f"Chunk length: {len(chunk)}")
            updated = update_chunk(chunk)
            total_updated += updated

        print(f"Total records processed: {total_updated}")

    except Exception as e:
        raise e  

if __name__ == '__main__':
    update_colin_ar_ind_flow()