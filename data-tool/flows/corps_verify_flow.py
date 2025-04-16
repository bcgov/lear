import math

import pandas as pd
from common.init_utils import colin_init, get_config, lear_init
from prefect import flow, task
from sqlalchemy import Engine, text


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


@task(name='1-Count')
def get_verify_count(colin_engine: Engine) -> int:
    with colin_engine.connect() as colin_conn:
        rs = colin_conn.execute(text(colin_cnt_query))
        total = rs.scalar()
        return total


@task(name='2-Verify')
def verify(colin_engine: Engine, lear_engine: Engine, limit: int, offset: int) -> list:

    identifiers = None

    with colin_engine.connect() as colin_conn:
        rs = colin_conn.execute(text(colin_query), {'limit': limit, 'offset': offset})
        colin_results = rs.fetchall()
        identifiers = [row[0] for row in colin_results]

    if identifiers:
        with lear_engine.connect() as lear_conn:
            rs = lear_conn.execute(text(lear_query), {'identifiers': identifiers})
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
        colin_engine = colin_init(config)
        lear_engine = lear_init(config)

        total = get_verify_count(colin_engine)

        if config.VERIFY_BATCH_SIZE <= 0:
            raise ValueError('VERIFY_BATCH_SIZE must be explicitly set to a positive integer')
        batch_size = config.VERIFY_BATCH_SIZE
        batches = math.ceil(total/batch_size)

        print(f'🚀 Verifying {total} busiesses...')

        cnt = 0
        offset = 0
        results = []
        futures = []
        while cnt < batches:
            print(f'🚀 Running {cnt} round...')
            futures.append(verify.submit(colin_engine, lear_engine, batch_size, offset))
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
