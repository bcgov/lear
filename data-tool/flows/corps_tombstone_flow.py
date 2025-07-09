import contextlib
import math
from collections import defaultdict
from datetime import datetime, timedelta
from http import HTTPStatus
from pathlib import Path

from common.auth_service import AuthService
from common.extract_tracking_service import \
    ExtractTrackingService as CorpProcessingService, ProcessingStatuses
from common.init_utils import colin_extract_init, get_config, lear_init
from common.query_utils import convert_result_set_to_dict
from prefect import flow, serve, task
from prefect.cache_policies import NO_CACHE
from prefect.context import get_run_context
from prefect.futures import wait
from prefect.states import Failed
from prefect.task_runners import ConcurrentTaskRunner
from prefect_dask import DaskTaskRunner
from sqlalchemy import Connection, text
from sqlalchemy.engine import Engine
from tombstone.tombstone_queries import (get_corp_snapshot_filings_queries,
                                         get_corp_users_query,
                                         get_total_unprocessed_count_query,
                                         get_unprocessed_corps_query)
from tombstone.tombstone_utils import (all_unsupported_types,
                                       build_epoch_filing, format_users_data,
                                       formatted_data_cleanup,
                                       get_data_formatters, load_data,
                                       update_data, update_versioning)


@task(cache_policy=NO_CACHE)
def reserve_unprocessed_corps(config, processing_service, flow_run_id, num_corps) -> list:
    """Reserve corps for a given flow run.

    Note that this is not same as claiming them for processing which will be done in some subsequent steps.  This step
    is done to avoid parallel flows from trying to compete for the same corps.
    """
    base_query = get_unprocessed_corps_query(
        'tombstone-flow',
        config,
        num_corps  # Pass the total number we want to process
    )

    # reserve corps
    reserved = processing_service.reserve_for_flow(base_query, flow_run_id)
    return reserved


@task(cache_policy=NO_CACHE)
def get_unprocessed_count(config, colin_engine: Engine) -> int:
    query = get_total_unprocessed_count_query(
        'tombstone-flow',
        config.DATA_LOAD_ENV
    )

    sql_text = text(query)

    with colin_engine.connect() as conn:
        rs = conn.execute(sql_text)
        total = rs.scalar()

        return total


@task(name='1.1-Users-Collect-Task', cache_policy=NO_CACHE)
def get_corp_users(colin_engine: Engine, corp_nums: list) -> list[dict]:
    """Get user information."""
    query = get_corp_users_query(corp_nums)
    sql_text = text(query)

    with colin_engine.connect() as conn:
        rs = conn.execute(sql_text)
        raw_data_dict = convert_result_set_to_dict(rs)
        return raw_data_dict


@task(name='1.2-Users-Migrate-Task', cache_policy=NO_CACHE)
def load_corp_users(lear_engine: Engine, users_data: list) -> dict:
    """Migrate user information."""
    users_mapper = {}
    with lear_engine.connect() as conn:
        try:
            for user in users_data:
                # TODO: distinguish users of the same username but different roles
                username = user['username']
                user_id = load_data(conn, 'users', user, 'username', versioned=False)
                users_mapper[username] = user_id
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

    return users_mapper


@task(name='2.1-Corp-Snapshot-Placeholder-Filings-Collect-Task', cache_policy=NO_CACHE)
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


@task(name='2.2-Corp-Snapshot-Placeholder-Filings-Cleanup-Task', cache_policy=NO_CACHE)
def clean_snapshot_filings_data(data: dict) -> dict:
    """Clean corp snapshot and placeholder filings data."""
    # TODO: raise error for none
    tombstone = {}
    formatters = get_data_formatters()
    for k, f in formatters.items():
        tombstone[k] = f(data)

    tombstone = formatted_data_cleanup(tombstone)

    return tombstone


@task(name='3.1-Corp-Snapshot-Migrate-Task', cache_policy=NO_CACHE)
def load_corp_snapshot(conn: Connection, tombstone_data: dict, users_mapper: dict, versioning_mapper: dict) -> int:
    """Migrate corp snapshot."""
    # Note: The business info is partially loaded for businesses table now. And it will be fully
    # updated by the following placeholder historical filings migration. But it depends on the
    # implementation of next step.
    business_id = load_data(conn, 'businesses', tombstone_data['businesses'], 'identifier', conflict_error=True)
    versioning_mapper['businesses_version'].append(business_id)

    for office in tombstone_data['offices']:
        office['offices']['business_id'] = business_id
        office_id = load_data(conn, 'offices', office['offices'])
        versioning_mapper['offices_version'].append(office_id)

        for address in office['addresses']:
            address['business_id'] = business_id
            address['office_id'] = office_id
            address_id = load_data(conn, 'addresses', address)
            versioning_mapper['addresses_version'].append(address_id)

    party_roles_map = {}
    for party in tombstone_data['parties']:
        mailing_address_id = None
        delivery_address_id = None
        for address in party['addresses']:
            address_id = load_data(conn, 'addresses', address)
            versioning_mapper['addresses_version'].append(address_id)
            if address['address_type'] == 'mailing':
                mailing_address_id = address_id
            else:
                delivery_address_id = address_id

        party['parties']['mailing_address_id'] = mailing_address_id
        party['parties']['delivery_address_id'] = delivery_address_id

        source_full_name = party['parties']['cp_full_name']
        del party['parties']['cp_full_name']
        party_id = load_data(conn, 'parties', party['parties'])
        versioning_mapper['parties_version'].append(party_id)

        for party_role in party['party_roles']:
            party_role['business_id'] = business_id
            party_role['party_id'] = party_id
            party_role_id = load_data(conn, 'party_roles', party_role, expecting_id=True)
            versioning_mapper['party_roles_version'].append(party_role_id)

            # Create a unique key for mapping
            key = (source_full_name, party_role['role'])
            party_roles_map[key] = party_role_id

    for office_held in tombstone_data.get('offices_held', []):
        # Map to party_role_id using the key
        key = (office_held['cp_full_name'], 'officer')
        party_role_id = party_roles_map.get(key)
        office_held['party_role_id'] = party_role_id
        del office_held['cp_full_name']
        office_held_id = load_data(conn, 'offices_held', office_held)
        versioning_mapper['offices_held_version'].append(office_held_id)

    for share_class in tombstone_data['share_classes']:
        share_class['share_classes']['business_id'] = business_id
        share_class_id = load_data(conn, 'share_classes', share_class['share_classes'])
        versioning_mapper['share_classes_version'].append(share_class_id)

        for share_series in share_class['share_series']:
            share_series['share_class_id'] = share_class_id
            share_series_id = load_data(conn, 'share_series', share_series)
            versioning_mapper['share_series_version'].append(share_series_id)

    for alias in tombstone_data['aliases']:
        alias['business_id'] = business_id
        alias_id = load_data(conn, 'aliases', alias)
        versioning_mapper['aliases_version'].append(alias_id)

    for resolution in tombstone_data['resolutions']:
        resolution['business_id'] = business_id
        resolution_id = load_data(conn, 'resolutions', resolution)
        versioning_mapper['resolutions_version'].append(resolution_id)

    for comment in tombstone_data['comments']:
        comment['business_id'] = business_id
        username = comment['staff_id']
        staff_id = users_mapper.get(username)
        comment['staff_id'] = staff_id
        load_data(conn, 'comments', comment, versioned=False)

    if in_dissolution := tombstone_data['in_dissolution']:
        batch = in_dissolution['batches']
        batch_id = load_data(conn, 'batches', batch, versioned=False)
        batch_processing = in_dissolution['batch_processing']

        batch_processing['batch_id'] = batch_id
        batch_processing['business_id'] = business_id
        load_data(conn, 'batch_processing', batch_processing, versioned=False)

        furnishing = in_dissolution['furnishings']
        furnishing['batch_id'] = batch_id
        furnishing['business_id'] = business_id
        load_data(conn, 'furnishings', furnishing, versioned=False)

    return business_id


@task(name='3.2.1-Placeholder-Historical-Filings-Migrate-Task', cache_policy=NO_CACHE)
def load_placeholder_filings(conn: Connection, tombstone_data: dict, business_id: int, users_mapper: dict, versioning_mapper: dict):
    """Migrate placeholder historical filings."""
    filings_data = tombstone_data['filings']
    update_info = tombstone_data['updates']
    state_filing_index = update_info['state_filing_index']
    update_business_data = update_info['businesses']
    filing_ids_mapper = {}
    # load placeholder filings
    for i, data in enumerate(filings_data):
        f = data['filings']
        transaction_id = load_data(conn, 'transaction', {'issued_at': datetime.utcnow().isoformat()}, versioned=False)
        username = f['submitter_id']
        user_id = users_mapper.get(username)
        f['submitter_id'] = user_id
        f['transaction_id'] = transaction_id
        f['business_id'] = business_id
        if (withdrawn_idx := f['withdrawn_filing_id']) is not None:
            f['withdrawn_filing_id'] = filing_ids_mapper[withdrawn_idx]

        filing_id = load_data(conn, 'filings', f, versioned=False)
        filing_ids_mapper[i] = filing_id

        data['colin_event_ids']['filing_id'] = filing_id
        load_data(conn, 'colin_event_ids', data['colin_event_ids'], expecting_id=False, versioned=False)

        if i == state_filing_index:
            update_info['businesses']['state_filing_id'] = filing_id

        if jurisdiction := data['jurisdiction']:
            jurisdiction['business_id'] = business_id
            jurisdiction['filing_id'] = filing_id
            jurisdiction_id = load_data(conn, 'jurisdictions', jurisdiction)
            versioning_mapper['jurisdictions_version'].append(jurisdiction_id)

        # load amalgamation snapshot linked to the current filing
        if amalgamation_data := data['amalgamations']:
            load_amalgamation_snapshot(conn, amalgamation_data, business_id, filing_id, versioning_mapper)

        if comments_data := data['comments']:
            for comment in comments_data:
                comment['business_id'] = business_id
                comment['filing_id'] = filing_id
                username = comment['staff_id']
                staff_id = users_mapper.get(username)
                comment['staff_id'] = staff_id
                load_data(conn, 'comments', comment, versioned=False)

        if cco_data := data['consent_continuation_out']:
            cco_data['business_id'] = business_id
            cco_data['filing_id'] = filing_id
            load_data(conn, 'consent_continuation_outs', cco_data, versioned=False)

    # load epoch filing
    epoch_filing_data = build_epoch_filing(business_id)
    transaction_id = load_data(conn, 'transaction', {'issued_at': datetime.utcnow().isoformat()}, versioned=False)
    epoch_filing_data['transaction_id'] = transaction_id
    load_data(conn, 'filings', epoch_filing_data, versioned=False)

    # load updates for business
    if update_business_data:
        update_data(conn, 'businesses', update_business_data, 'id', business_id)

    return transaction_id


@task(name='3.2.2-Amalgamation-Snapshot-Migrate-Task', cache_policy=NO_CACHE)
def load_amalgamation_snapshot(conn: Connection, amalgamation_data: dict, business_id: int, filing_id: int, versioning_mapper: dict):
    """Migrate amalgamation snapshot."""
    amalgamation = amalgamation_data['amalgamations']
    amalgamation['business_id'] = business_id
    amalgamation['filing_id'] = filing_id
    amalgamation_id = load_data(conn, 'amalgamations', amalgamation)
    versioning_mapper['amalgamations_version'].append(amalgamation_id)

    for ting in amalgamation_data['amalgamating_businesses']:
        if ting_identifier := ting.get('ting_identifier'):
            # TODO: avoid update info for withdrawn amalg filing (will handle in NoW work)
            # TING must exists in db before updating state filing info,
            del ting['ting_identifier']
            temp_ting = {
                'identifier': ting_identifier,
                'state_filing_id': filing_id,
                'dissolution_date': amalgamation['amalgamation_date']
            }
            ting_business_id = update_data(conn, 'businesses', temp_ting, 'identifier', ting_identifier)
            if not ting_business_id:
                raise Exception(f'TING {ting_identifier} does not exist, cannot migrate TED before TING')
            ting['business_id'] = ting_business_id
        ting['amalgamation_id'] = amalgamation_id
        amalgamating_business_id = load_data(conn, 'amalgamating_businesses', ting)
        versioning_mapper['amalgamating_businesses_version'].append(amalgamating_business_id)


@task(name='3.3-Update-Auth-Task', cache_policy=NO_CACHE)
def update_auth(conn: Connection, config, corp_num: str, tombstone_data: dict):
    """Create auth entity and affiliate as required."""
    # Note: affiliation to an account does not need to happen.  only entity creation in auth is req'd.
    #  used for testing purposes to see how things look in entity dashboard
    pass_code = tombstone_data.get('pass_code')
    if config.USE_CUSTOM_PASSCODE:
        pass_code = config.CUSTOM_PASSCODE

    if config.UPDATE_ENTITY:
        business_data = tombstone_data['businesses']
        entity_status = AuthService.create_entity(
            config=config,
            business_registration=business_data['identifier'],
            business_name=business_data['legal_name'],
            corp_type_code=business_data['legal_type'],
            pass_code=pass_code
        )

        admin_email = tombstone_data.get('admin_email')
        if config.USE_CUSTOM_CONTACT_EMAIL:
            admin_email = config.CUSTOM_CONTACT_EMAIL

        if entity_status == HTTPStatus.OK and admin_email:
            update_email_status = AuthService.update_contact_email(
                config=config,
                identifier=business_data['identifier'],
                email=admin_email
            )
            if update_email_status != HTTPStatus.OK:
                raise Exception(f"""Failed to update admin email in auth {business_data['identifier']}""")
        else:
            raise Exception(f"""Failed to create entity in auth {business_data['identifier']}""")

    if config.AFFILIATE_ENTITY:
        business_data = tombstone_data['businesses']
        account_id = config.AFFILIATE_ENTITY_ACCOUNT_ID
        affiliation_status = AuthService.create_affiliation(
            config=config,
            account=account_id,
            business_registration=business_data['identifier'],
            business_name=business_data['legal_name'],
            corp_type_code=business_data['legal_type'],
            pass_code=pass_code,
            details={
                'identifier': business_data['identifier']
            }
        )
        if affiliation_status != HTTPStatus.OK:
            with contextlib.suppress(Exception):
                AuthService.delete_affiliation(
                    config=config,
                    account=account_id,
                    business_registration=business_data['identifier'])
            raise Exception(f"""Failed to affiliate business {business_data['identifier']}""")


@task(name='1-Migrate-Corp-Users-Task', cache_policy=NO_CACHE)
def migrate_corp_users(colin_engine: Engine, lear_engine: Engine, corp_nums: list) -> dict:
    try:
        print(f'👷 Start collecting and migrating users for {len(corp_nums)} corps: {", ".join(corp_nums[:5])}...')
        raw_data = get_corp_users(colin_engine, corp_nums)
        clean_data = format_users_data(raw_data)
        users_mapper = load_corp_users(lear_engine, clean_data)
        print(f'👷 Complete collecting and migrating users for {len(corp_nums)} corps: {", ".join(corp_nums[:5])}...')
    except Exception as e:
        print(f'❌ Error collecting and migrating users: {repr(e)}')
        raise e

    return users_mapper


@task(name='2-Get-Corp-Tombstone-Data-Task-Async', cache_policy=NO_CACHE)
def get_tombstone_data(config, colin_engine: Engine, corp_num: str) -> tuple[str, dict]:
    """Get tombstone data - corp snapshot and placeholder filings."""
    try:
        print(f'👷 Start collecting corp snapshot and filings data for {corp_num}...')
        raw_data = get_snapshot_filings_data(config, colin_engine, corp_num)
        # print(f'raw data: {raw_data}')
        clean_data = clean_snapshot_filings_data(raw_data)
        # print(f'clean data: {clean_data}')
        print(f'👷 Complete collecting corp snapshot and filings data for {corp_num}!')
        return corp_num, clean_data
    except Exception as e:
        print(f'❌ Error collecting corp snapshot and filings data for {corp_num}: {repr(e)}')
        return corp_num, e


@task(name='3-Corp-Tombstone-Migrate-Task-Async', cache_policy=NO_CACHE)
def migrate_tombstone(config, lear_engine: Engine, corp_num: str, clean_data: dict, users_mapper: dict) -> str:
    """Migrate tombstone data - corp snapshot and placeholder filings."""
    # TODO: update corp_processing status (succeeded & failed)
    # TODO: determine the time to update some business values based off filing info
    print(f'👷 Start migrating {corp_num}...')
    with lear_engine.connect() as lear_conn:
        transaction = lear_conn.begin()
        try:
            versioning_mapper = defaultdict(list)
            business_id = load_corp_snapshot(
                lear_conn, clean_data, users_mapper, versioning_mapper)
            tombstone_transaction_id = load_placeholder_filings(
                lear_conn,
                clean_data,
                business_id,
                users_mapper,
                versioning_mapper)
            update_versioning(
                lear_conn, tombstone_transaction_id, versioning_mapper)
            update_auth(lear_conn, config, corp_num, clean_data)
            transaction.commit()
        except Exception as e:
            transaction.rollback()
            print(f'❌ Error migrating corp snapshot and filings data for {corp_num}: {repr(e)}')
            return corp_num, e
    print(f'✅ Complete migrating {corp_num}!')

    additional_info = clean_data['unsupported_types']
    return corp_num, additional_info


@flow(
    name='Corps-Tombstone-Migrate-Flow',
    log_prints=True,
    persist_result=False,
    # use ConcurrentTaskRunner when using work pool based deployments
    # task_runner=ConcurrentTaskRunner(max_workers=100)
    # task_runner=DaskTaskRunner(cluster_kwargs={"n_workers": 3, "threads_per_worker": 2})
)
def tombstone_flow():
    """Entry of tombstone pipeline"""
    # TODO: track migration progress + error handling
    # TODO: update unprocessed query + count query
    # TODO: current pipeline doesn't support migrating TED & TING at the same time, need a better strategy
    try:
        config = get_config()
        colin_engine = colin_extract_init(config)
        lear_engine = lear_init(config)
        flow_run_id = get_run_context().flow_run.id
        processing_service = CorpProcessingService(config.DATA_LOAD_ENV, colin_engine, 'tombstone-flow')

        total = get_unprocessed_count(config, colin_engine)

        if config.TOMBSTONE_BATCHES <= 0:
            raise ValueError('TOMBSTONE_BATCHES must be explicitly set to a positive integer')
        if config.TOMBSTONE_BATCH_SIZE <= 0:
            raise ValueError('TOMBSTONE_BATCH_SIZE must be explicitly set to a positive integer')
        batch_size = config.TOMBSTONE_BATCH_SIZE
        batches = min(math.ceil(total/batch_size), config.TOMBSTONE_BATCHES)

        # Calculate max corps to initialize
        max_corps = min(total, config.TOMBSTONE_BATCHES * config.TOMBSTONE_BATCH_SIZE)
        print(f'👷 max_corps: {max_corps}')
        reserved_corps = reserve_unprocessed_corps(config, processing_service, flow_run_id, max_corps)
        print(f'👷 Reserved {reserved_corps} corps for processing')
        print(f'👷 Going to migrate {total} corps with batch size of {batch_size}')

        cnt = 0
        migrated_cnt = 0
        total_corp_failed = 0
        is_user_failed = False
        while cnt < batches:
            # Claim next batch of reserved corps for current flow
            corp_nums = processing_service.claim_batch(flow_run_id, batch_size)
            if not corp_nums:
                print("No more corps available to claim")
                break

            print(f'👷 Start processing {len(corp_nums)} corps: {", ".join(corp_nums[:5])}...')

            try:
                users_mapper = migrate_corp_users(colin_engine, lear_engine, corp_nums)
            except Exception as e:
                # skip migration if there's user migration error
                print('❗ Skip corp migration in this round due to user migration error.')
                for corp_num in corp_nums:
                    processing_service.update_corp_status(
                        flow_run_id,
                        corp_num,
                        ProcessingStatuses.FAILED,
                        error=f'Failed due to user migration error in round {cnt}: {repr(e)}'
                    )
                is_user_failed = True
                continue

            data_futures = []
            for corp_num in corp_nums:
                data_futures.append(
                    get_tombstone_data.submit(config, colin_engine, corp_num)
                )

            corp_futures = []
            failed = 0
            for f in data_futures:
                corp_num, clean_data = f.result()
                if clean_data and not isinstance(clean_data, Exception):
                    corp_futures.append(
                        migrate_tombstone.submit(config, lear_engine, corp_num, clean_data, users_mapper)
                    )
                else:
                    failed += 1
                    processing_service.update_corp_status(
                        flow_run_id,
                        corp_num,
                        ProcessingStatuses.FAILED,
                        error=f'Failed due to data collection error: {repr(clean_data)}'
                    )
                    print(f'❗ Skip migrating {corp_num} due to data collection error.')

            wait(corp_futures)
            complete = 0
            partial = 0
            for f in corp_futures:
                corp_num, e = f.result()
                if not e:
                    complete += 1
                    processing_service.update_corp_status(
                        flow_run_id,
                        corp_num,
                        ProcessingStatuses.COMPLETED
                    )
                elif isinstance(e, Exception):
                    # Handle error case if needed
                    failed += 1
                    processing_service.update_corp_status(
                        flow_run_id,
                        corp_num,
                        ProcessingStatuses.FAILED,
                        error=f'Failed due to {repr(e)}'
                    )
                else:
                    partial += 1
                    processing_service.update_corp_status(
                        flow_run_id,
                        corp_num,
                        ProcessingStatuses.PARTIAL,
                        error=f"Partial due to unsupported event_file types: {', '.join(e)}"
                    )

            total_corp_failed += failed
            print(f'🌟 Complete round {cnt}. Complete: {complete}. Partial: {partial}. Failed: {failed}.')
            cnt += 1
            migrated_cnt += complete + partial

        print(f'🌰 Complete {cnt} rounds, migrate {migrated_cnt} corps.')
        print(f"🌰 All unsupport event file types: {', '.join(all_unsupported_types)}")

        if is_user_failed:
            return Failed(message='Failed due to user migration error.')
        if total_corp_failed > 0:
            return Failed(message=f'{total_corp_failed} corps failed due to corp migration error.')

    except Exception as e:
        raise e


if __name__ == "__main__":
    tombstone_flow()

    # # Create deployment - only intended to test locally for parallel flows
    # deployment = tombstone_flow.to_deployment(
    #     name="tombstone-deployment",
    #     interval=timedelta(seconds=8),  # Run every x seconds
    #     tags=["tombstone-migration"]
    # )
    #
    # # Start serving the deployment
    # serve(deployment)


    # Work pool based deployments
    #
    # Only one of deployments 1-3 should be running at any given time.
    #
    # Note: the following deployment is used strictly for maximizing local resource usage for production
    # dry runs and the actual final tombstone migration to the production environment.  If there is no need
    # to run multiple parallel flows, the following set-ups are not req'd.

    # flow_source = Path(__file__).parent

    # # 1. TINGs deployment setup
    # # subquery = subqueries[1]
    # # ensure "and cs.state_type_cd = 'ACT'" is commented out as TINGS are historical
    # tombstone_flow.from_source(
    #     source=flow_source,
    #     entrypoint="corps_tombstone_flow.py:tombstone_flow"
    # ).deploy(
    #     name="tombstone-tings-deployment",
    #     tags=["tombstone-tings-migration"],
    #     work_pool_name="tombstone-tings-pool",
    #     interval=timedelta(seconds=60)  # Run every x seconds
    # )

    # # 2. TEDs deployment setup
    # # subquery = subqueries[2]
    # tombstone_flow.from_source(
    #     source=flow_source,
    #     entrypoint="corps_tombstone_flow.py:tombstone_flow"
    # ).deploy(
    #     name="tombstone-teds-deployment",
    #     tags=["tombstone-teds-migration"],
    #     work_pool_name="tombstone-teds-pool",
    #     interval=timedelta(seconds=60)  # Run every x seconds
    # )

    # # 3. OTHERs deployment setup
    # # subquery = subqueries[3]
    # tombstone_flow.from_source(
    #     source=flow_source,
    #     entrypoint="corps_tombstone_flow.py:tombstone_flow"
    # ).deploy(
    #     name="tombstone-deployment",
    #     tags=["tombstone-migration"],
    #     work_pool_name="tombstone-pool",
    #     interval=timedelta(seconds=70)  # Run every x seconds
    # )
