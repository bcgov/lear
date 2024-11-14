import math

from common.init_utils import colin_init, get_config, lear_init
from common.query_utils import convert_result_set_to_dict
from prefect import flow, task
from prefect.futures import wait
from sqlalchemy import Connection, text
from sqlalchemy.engine import Engine
from tombstone.tombstone_queries import (get_corp_snapshot_queries,
                                         get_total_unprocessed_count_query,
                                         get_unprocessed_corps_query)
from tombstone.tombstone_utils import get_snapshot_data_formatters, load_data


@task
def get_unprocessed_corps(config, colin_engine: Engine) -> list:
    """Get unprocessed corp numbers."""
    query = get_unprocessed_corps_query(
        'local',
        config.DATA_LOAD_ENV,
        config.BATCH_SIZE
    )
    sql_text = text(query)

    with colin_engine.connect() as conn:
        rs = conn.execute(sql_text)
        raw_data_dict = convert_result_set_to_dict(rs)
        corp_nums = [x.get('corp_num') for x in raw_data_dict]
        return corp_nums


def get_unprocessed_count(config, colin_engine: Engine) -> int:
    query = get_total_unprocessed_count_query(
        'local',
        config.DATA_LOAD_ENV
    )

    sql_text = text(query)

    with colin_engine.connect() as conn:
        rs = conn.execute(sql_text)
        total = rs.scalar()

        return total


@task
def get_snapshot_filings_data(config, colin_engine: Engine, corp_num: str) -> dict:
    """Get corp snapshot and placeholder filings data."""
    raw_data = {}
    queries = get_corp_snapshot_queries(config, corp_num)

    with colin_engine.connect() as conn:
        for k, q in queries.items():
            rs = conn.execute(text(q))
            raw_dict = convert_result_set_to_dict(rs)
            raw_data[k] = raw_dict

        return raw_data


def clean_snapshot_filings_data(data: dict) -> dict:
    """Clean corp snapshot and placeholder filings data."""
    # TODO: raise error for none
    snapshot = {}
    formatters = get_snapshot_data_formatters()
    for k, f in formatters.items():
        snapshot[k] = f(data)
    return snapshot


@task(name='2.1-Corp-Snapshot-Migrate-Task')
def load_corp_snapshot(conn: Connection, snapshot_data: dict) -> dict:
    """Migrate corp snapshot."""
    # Note: The business info is partially loaded for businesses table now. And it will be fully
    # updated by the following placeholder historical filings migration. But it depends on the
    # implementation of next step.
    business_id = load_data(conn, 'businesses', snapshot_data['businesses'])

    for office in snapshot_data['offices']:
        office['offices']['business_id'] = business_id
        office_id = load_data(conn, 'offices', office['offices'])

        for address in office['addresses']:
            address['business_id'] = business_id
            address['office_id'] = office_id
            load_data(conn, 'addresses', address)

    for party in snapshot_data['parties']:
        mailing_address_id = None
        delivery_address_id = None
        for address in party['addresses']:
            address_id = load_data(conn, 'addresses', address)
            if address['address_type'] == 'mailing':
                mailing_address_id = address_id
            else:
                delivery_address_id = address_id
        
        party['parties']['mailing_address_id'] = mailing_address_id
        party['parties']['delivery_address_id'] = delivery_address_id

        party_id = load_data(conn, 'parties', party['parties'])

        for party_role in party['party_roles']:
            party_role['business_id'] = business_id
            party_role['party_id'] = party_id
            load_data(conn, 'party_roles', party_role)
    
    for share_class in snapshot_data['share_classes']:
        share_class['share_classes']['business_id'] = business_id
        share_class_id = load_data(conn, 'share_classes', share_class['share_classes'])

        for share_series in share_class['share_series']:
            share_series['share_class_id'] = share_class_id
            load_data(conn, 'share_series', share_series)
    
    for alias in snapshot_data['aliases']:
        alias['business_id'] = business_id
        load_data(conn, 'aliases', alias)
    
    for resolution in snapshot_data['resolutions']:
        resolution['business_id'] = business_id
        load_data(conn, 'resolutions', resolution)


@task(name='2.2-Placeholder-Historical-Filings-Migrate-Task')
def load_placeholder_filings(config, lear_conn: Connection, corp_num: str):
    """Migrate placeholder historical filings."""
    # load placeholder filings
    # load epoch filing
    pass


@task(name='1-Get-Corp-Tombstone-Data-Task')
def get_tombstone_data(config, colin_engine: Engine, corp_num: str) -> tuple[str, dict]:
    """Get tombstone data - corp snapshot and placeholder filings."""
    try:
        # TODO: get filings data
        print(f'👷 Start collecting corp snapshot and filings data for {corp_num}...')  
        raw_data = get_snapshot_filings_data(config, colin_engine, corp_num)
        # print(f'raw data: {raw_data}')
        clean_data = clean_snapshot_filings_data(raw_data)
        # print(f'clean data: {clean_data}')
        print(f'👷 Complete collecting corp snapshot and filings data for {corp_num}!')  
        return corp_num, clean_data
    except Exception as e:
        print(f'❌ Error collecting corp snapshot and filings data for {corp_num}: {repr(e)}')
        return corp_num, None


@task(name='2-Corp-Tombstone-Migrate-Task')
def migrate_tombstone(config, lear_engine: Engine, corp_num: str, clean_data: dict) -> str:
    """Migrate tombstone data - corp snapshot and placeholder filings."""
    # TODO: update corp_processing status (succeeded & failed)
    # TODO: determine the time to update some business values based off filing info
    print(f'👷 Start migrating {corp_num}...')
    with lear_engine.connect() as lear_conn:
        transaction = lear_conn.begin()
        try:
            load_corp_snapshot(lear_conn, clean_data)
            load_placeholder_filings(config, lear_conn, clean_data)
            transaction.commit()
        except Exception as e:
            transaction.rollback()
            raise e
    print(f'✅ Complete migrating {corp_num}!')
    return corp_num


@flow(
    name='Corps-Tombstone-Migrate-Flow',
    log_prints=True,
    persist_result=False
)
def tombstone_flow():
    """Entry of tombstone pipeline"""
    # TODO: track migration progress + error handling
    # TODO: update unprocessed query + count query
    try:
        config = get_config()
        colin_engine = colin_init(config)
        lear_engine = lear_init(config)

        total = get_unprocessed_count(config, colin_engine)

        if config.BATCHES <= 0:
            raise ValueError('BATCHES must be explicitly set to a positive integer')
        if config.BATCH_SIZE <= 0:
            raise ValueError('BATCH_SIZE must be explicitly set to a positive integer')
        batch_size = config.BATCH_SIZE
        batches = min(math.ceil(total/batch_size), config.BATCHES)

        print(f'👷 Going to migrate {total} corps with batch size of {batch_size}')
        
        cnt = 0
        migrated_cnt = 0
        while cnt < batches:
            corp_nums = get_unprocessed_corps(config, colin_engine)
            print(f'👷 Start processing {len(corp_nums)} corps: {", ".join(corp_nums[:5])}...')
            data_futures = []
            for corp_num in corp_nums:
                data_futures.append(
                    get_tombstone_data.submit(config, colin_engine, corp_num)
                )

            corp_futures = []
            skipped = 0
            for f in data_futures:
                corp_num, clean_data = f.result()
                if clean_data:
                    corp_futures.append(
                        migrate_tombstone.submit(config, lear_engine, corp_num, clean_data)
                    )
                else:
                    skipped += 1
                    print(f'❗ Skip migrating {corp_num} due to data collection error.')

            wait(corp_futures)
            succeeded = sum(1 for f in corp_futures if f.state.is_completed())
            failed = len(corp_futures) - succeeded
            print(f'🌟 Complete round {cnt}. Succeeded: {succeeded}. Failed: {failed}. Skip: {skipped}')
            cnt += 1
            migrated_cnt += succeeded

        print(f'🌰 Complete {cnt} rounds, migrate {migrated_cnt} corps.')

    except Exception as e:
        raise e


if __name__ == "__main__":
    tombstone_flow()