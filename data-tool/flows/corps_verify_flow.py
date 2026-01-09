import math

import pandas as pd
from common.init_utils import colin_extract_init, get_config, lear_init
from typing import List
from prefect import flow, task
from prefect.cache_policies import NO_CACHE
from sqlalchemy import Engine, text, bindparam


# TODO: adjust clause in different phases
where_clause = """
1 = 1
"""

colin_cnt_query = f"""
    SELECT COUNT(*) FROM corporation c WHERE {where_clause}
    """

colin_query = f"""
    SELECT corp_num FROM corporation c WHERE {where_clause} ORDER BY corp_num LIMIT :limit OFFSET :offset
"""

lear_query = f"""
    SELECT colin_corps.identifier FROM UNNEST(ARRAY[:identifiers]) AS colin_corps(identifier)
    LEFT JOIN businesses b on colin_corps.identifier = b.identifier
    WHERE b.identifier IS NULL
"""

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


def _parse_csv(csv_val: str) -> List[int]:
    if not csv_val:
        return []

    return [
        int(token)
        for token in (t.strip() for t in csv_val.split(','))
        if token.isdigit()
    ]


@task(cache_policy=NO_CACHE)
def get_mig_corp_candidates(config, colin_engine: Engine) -> List[str]:
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
        return candidates


@task(name='1-Count', cache_policy=NO_CACHE)
def get_verify_count(colin_engine: Engine) -> int:
    with colin_engine.connect() as colin_conn:
        rs = colin_conn.execute(text(colin_cnt_query))
        total = rs.scalar()
        return total


@task(name='2-Verify', cache_policy=NO_CACHE)
def verify(colin_engine: Engine, lear_engine: Engine,
           mig_corp_candidates: List[str], limit: int, offset: int) -> list:

    identifiers = None

    if mig_corp_candidates is not None and len(mig_corp_candidates) > 0:
        identifiers = mig_corp_candidates[offset:offset+limit]
    else:
        with colin_engine.connect() as colin_conn:
            rs = colin_conn.execute(text(colin_query),
                                    {'limit': limit, 'offset': offset})
            colin_results = rs.fetchall()
            identifiers = [row[0] for row in colin_results]

    # Now check LEAR for missing corps
    if identifiers:
        with lear_engine.connect() as lear_conn:
            rs = lear_conn.execute(text(lear_query),
                                   {'identifiers': identifiers})
            lear_results = rs.fetchall()
            missing = [row[0] for row in lear_results]
            return missing

    return []


@flow(
    name='Corps-Tombstone-Verify-Flow',
    log_prints=True,
    persist_result=False,
)
def verify_flow():
    try:
        config = get_config()
        colin_engine = colin_extract_init(config)
        lear_engine = lear_init(config)

        # Determine mode
        mig_mode = bool(config.USE_MIGRATION_FILTER)
        mig_corp_candidates: List[str] = []
        if mig_mode:
            mig_corp_candidates = get_mig_corp_candidates(config, colin_engine)
            print(f'👷 Using MIG filter mode with {len(mig_corp_candidates)} candidates')

        # Get total count based on mode (config.USE_MIGRATION_FILTER)
        if config.USE_MIGRATION_FILTER and mig_corp_candidates is not None:
            total = len(mig_corp_candidates)
        else:
            total = get_verify_count(colin_engine)

        if config.VERIFY_BATCHES <= 0:
            raise ValueError('VERIFY_BATCHES must be explicitly set to a positive integer')
        if config.VERIFY_BATCH_SIZE <= 0:
            raise ValueError('VERIFY_BATCH_SIZE must be explicitly set to a positive integer')
        batch_size = config.VERIFY_BATCH_SIZE

        # Determine number of batches based on mode (config.USE_MIGRATION_FILTER)
        if mig_mode:
            batches = min(math.ceil(total/batch_size), config.VERIFY_BATCHES)
        else:
            batches = math.ceil(total/batch_size)

        print(f'🚀 Verifying {total} busiesses...')

        cnt = 0
        offset = 0
        results = []
        futures = []
        while cnt < batches:
            print(f'🚀 Running {cnt} round...')
            futures.append(verify.submit(colin_engine, lear_engine,
                                         mig_corp_candidates, batch_size,
                                         offset))
            offset += batch_size
            cnt += 1

        for f in futures:
            r = f.result()
            results.extend(r)

        print(f'🌟 Complete round {cnt}')

        if summary_path:=config.VERIFY_SUMMARY_PATH:
            df = pd.DataFrame(results, columns=['identifier'])
            df.to_csv(summary_path, index=False)
            print(f"🌰 Save {len(results)} corps which meet the selection criteria but don't exsit in LEAR to {summary_path}")
        else:
            print(f"🌰 {len(results)} corps which meet the selection criteria don't exsit in LEAR: {results}")

    except Exception as e:
        raise e


if __name__ == '__main__':
    verify_flow()
