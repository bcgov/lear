import math
from datetime import datetime

from common.init_utils import colin_init, get_config, lear_init
from common.query_utils import convert_result_set_to_dict
from prefect import flow, task
from prefect.futures import wait
from sqlalchemy import Connection, text
from sqlalchemy.engine import Engine
from tombstone.tombstone_queries import (get_corp_snapshot_filings_queries,
                                         get_corp_users_query,
                                         get_total_unprocessed_count_query,
                                         get_unprocessed_corps_query)
from tombstone.tombstone_utils import (build_epoch_filing, format_users_data,
                                       formatted_data_cleanup,
                                       get_data_formatters, load_data,
                                       unsupported_event_file_types,
                                       update_data)


@task
def get_unprocessed_corps(config, colin_engine: Engine) -> list:
    """Get unprocessed corp numbers."""
    query = get_unprocessed_corps_query(
        'local',
        config.DATA_LOAD_ENV,
        config.TOMBSTONE_BATCH_SIZE
    )
    sql_text = text(query)

    with colin_engine.connect() as conn:
        rs = conn.execute(sql_text)
        raw_data_dict = convert_result_set_to_dict(rs)
        corp_nums = [x.get('corp_num') for x in raw_data_dict]
        return corp_nums


@task
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


@task(name='1.1-Users-Collect-Task')
def get_corp_users(colin_engine: Engine, corp_nums: list) -> list[dict]:
    """Get user information."""
    query = get_corp_users_query(corp_nums)

    sql_text = text(query)

    with colin_engine.connect() as conn:
        rs = conn.execute(sql_text)
        raw_data_dict = convert_result_set_to_dict(rs)
        return raw_data_dict


@task(name='1.2-Users-Migrate-Task')
def load_corp_users(lear_engine: Engine, users_data: list) -> dict:
    """Migrate user information."""
    users_mapper = {}
    with lear_engine.connect() as conn:
        try:
            for user in users_data:
                # TODO: distinguish users of the same username but different roles
                username = user['username']
                user_id = load_data(conn, 'users', user, 'username')
                users_mapper[username] = user_id
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

    return users_mapper


@task(name='2.1-Corp-Snapshot-Placeholder-Filings-Collect-Task')
def get_snapshot_filings_data(config, colin_engine: Engine, corp_num: str) -> dict:
    """Get corp snapshot and placeholder filings data."""
    raw_data = {}
    queries = get_corp_snapshot_filings_queries(config, corp_num)

    with colin_engine.connect() as conn:
        for k, q in queries.items():
            rs = conn.execute(text(q))
            raw_dict = convert_result_set_to_dict(rs)
            raw_data[k] = raw_dict

        return raw_data

@task(name='2.2-Corp-Snapshot-Placeholder-Filings-Cleanup-Task')
def clean_snapshot_filings_data(data: dict) -> dict:
    """Clean corp snapshot and placeholder filings data."""
    # TODO: raise error for none
    tombstone = {}
    formatters = get_data_formatters()
    for k, f in formatters.items():
        tombstone[k] = f(data)

    tombstone = formatted_data_cleanup(tombstone)

    return tombstone


@task(name='3.1-Corp-Snapshot-Migrate-Task')
def load_corp_snapshot(conn: Connection, tombstone_data: dict) -> int:
    """Migrate corp snapshot."""
    # Note: The business info is partially loaded for businesses table now. And it will be fully
    # updated by the following placeholder historical filings migration. But it depends on the
    # implementation of next step.
    business_id = load_data(conn, 'businesses', tombstone_data['businesses'])

    for office in tombstone_data['offices']:
        office['offices']['business_id'] = business_id
        office_id = load_data(conn, 'offices', office['offices'])

        for address in office['addresses']:
            address['business_id'] = business_id
            address['office_id'] = office_id
            load_data(conn, 'addresses', address)

    for party in tombstone_data['parties']:
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
    
    for share_class in tombstone_data['share_classes']:
        share_class['share_classes']['business_id'] = business_id
        share_class_id = load_data(conn, 'share_classes', share_class['share_classes'])

        for share_series in share_class['share_series']:
            share_series['share_class_id'] = share_class_id
            load_data(conn, 'share_series', share_series)
    
    for alias in tombstone_data['aliases']:
        alias['business_id'] = business_id
        load_data(conn, 'aliases', alias)
    
    for resolution in tombstone_data['resolutions']:
        resolution['business_id'] = business_id
        load_data(conn, 'resolutions', resolution)

    return business_id


@task(name='3.2-Placeholder-Historical-Filings-Migrate-Task')
def load_placeholder_filings(conn: Connection, tombstone_data: dict, business_id: int, users_mapper: dict):
    """Migrate placeholder historical filings."""
    filings_data = tombstone_data['filings']
    update_info = tombstone_data['updates']
    state_filing_index = update_info['state_filing_index']
    update_business_data = update_info['businesses']
    # load placeholder filings
    for i, f in enumerate(filings_data):
        transaction_id = load_data(conn, 'transaction', {'issued_at': datetime.utcnow().isoformat()})
        username = f['submitter_id']
        user_id  = users_mapper.get(username)
        f['submitter_id'] = user_id
        f['transaction_id'] = transaction_id
        f['business_id'] = business_id
        filing_id = load_data(conn, 'filings', f)

        if i == state_filing_index:
            update_info['businesses']['state_filing_id'] = filing_id

    # load epoch filing
    epoch_filing_data = build_epoch_filing(business_id)
    load_data(conn, 'filings', epoch_filing_data)

    # load updates for business
    if update_business_data:
        update_data(conn, 'businesses', update_business_data, business_id)


@task(name='1-Migrate-Corp-Users-Task')
def migrate_corp_users(colin_engine: Engine, lear_engine: Engine, corp_nums: list) -> dict:
    try:
        print(f'👷 Start collecting and migrating users for {len(corp_nums)} corps: {", ".join(corp_nums[:5])}...')
        raw_data = get_corp_users(colin_engine, corp_nums)
        clean_data = format_users_data(raw_data)
        users_mapper = load_corp_users(lear_engine, clean_data)
        print(f'👷 Complete collecting and migrating users for {len(corp_nums)} corps: {", ".join(corp_nums[:5])}...')
    except Exception as e:
        print(f'❌ Error collecting and migrating users: {repr(e)}')
        return None

    return users_mapper


@task(name='2-Get-Corp-Tombstone-Data-Task-Async')
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


@task(name='3-Corp-Tombstone-Migrate-Task-Aync')
def migrate_tombstone(lear_engine: Engine, corp_num: str, clean_data: dict, users_mapper: dict) -> str:
    """Migrate tombstone data - corp snapshot and placeholder filings."""
    # TODO: update corp_processing status (succeeded & failed)
    # TODO: determine the time to update some business values based off filing info
    print(f'👷 Start migrating {corp_num}...')
    with lear_engine.connect() as lear_conn:
        transaction = lear_conn.begin()
        try:
            business_id = load_corp_snapshot(lear_conn, clean_data)
            load_placeholder_filings(lear_conn, clean_data, business_id, users_mapper)
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

        if config.TOMBSTONE_BATCHES <= 0:
            raise ValueError('TOMBSTONE_BATCHES must be explicitly set to a positive integer')
        if config.TOMBSTONE_BATCH_SIZE <= 0:
            raise ValueError('TOMBSTONE_BATCH_SIZE must be explicitly set to a positive integer')
        batch_size = config.TOMBSTONE_BATCH_SIZE
        batches = min(math.ceil(total/batch_size), config.TOMBSTONE_BATCHES)

        print(f'👷 Going to migrate {total} corps with batch size of {batch_size}')
        
        cnt = 0
        migrated_cnt = 0
        while cnt < batches:
            corp_nums = get_unprocessed_corps(config, colin_engine)

            print(f'👷 Start processing {len(corp_nums)} corps: {", ".join(corp_nums[:5])}...')

            users_mapper = migrate_corp_users(colin_engine, lear_engine, corp_nums)

            # TODO: skip the following migration or continue?
            if users_mapper is None:
                print(f'❗ Skip populating user info for corps in this round due to user migration error.')
                users_mapper = {}
            
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
                        migrate_tombstone.submit(lear_engine, corp_num, clean_data, users_mapper)
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
        print(f"🌰 All unsupport event file types: {', '.join(unsupported_event_file_types)}")

    except Exception as e:
        raise e


if __name__ == "__main__":
    tombstone_flow()