import math
from collections import defaultdict
from contextlib import contextmanager
from http import HTTPStatus

import requests
from common.init_utils import colin_init, get_config, lear_init
from prefect import flow, task
from prefect.futures import wait
from sqlalchemy import Connection, text
from sqlalchemy.engine import Engine

businesses_cnt_query = """
SELECT COUNT(*) FROM businesses
WHERE 1 = 1
AND legal_type IN ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE', 'BEN')
AND legal_name LIKE '%' || :corp_name_suffix
"""

identifiers_query = """
SELECT id, identifier FROM businesses
WHERE 1 = 1 
AND legal_type IN ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE', 'BEN')
AND legal_name LIKE '%' || :corp_name_suffix
LIMIT :batch_size
"""


@contextmanager
def replica_role(conn: Connection):
    try:
        conn.execute(text("SET session_replication_role = 'replica';"))
        yield
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f'DB operations rollback due to error:\n {e}')
        raise e


@task
def get_selected_corps(db_engine: Engine, config):
    with db_engine.connect() as conn:
        results = conn.execute(text(identifiers_query), {
            'batch_size': config.DELETE_BATCH_SIZE,
            'corp_name_suffix': config.CORP_NAME_SUFFIX
            })

        rows = results.fetchall()

        if not rows:
            return None, None
        else:
            ids, identifiers = zip(*rows)
            return list(ids), list(identifiers)


@task
def lear_delete_non_versioned(conn: Connection, business_ids: list):
    # first query
    query_plans_one = [
        {
            'source': 'offices',
            'params': {'business_id': business_ids},
        },
        {
            'source': 'addresses',
            'params': {'business_id': business_ids},
        },
        {
            'source': 'party_roles',
            'columns': ['id', 'party_id'],
            'params': {'business_id': business_ids},
            'targets': ['party_roles', 'parties']
        },
        {
            'source': 'share_classes',
            'params': {'business_id': business_ids},
        },
        {
            'source': 'aliases',
            'params': {'business_id': business_ids},
        },
        {
            'source': 'resolutions',
            'params': {'business_id': business_ids},
        },
        {
            'source': 'amalgamations',
            'params': {'business_id': business_ids},
        },
    ]

    query_futures_one = []
    for plan in query_plans_one:
        query_futures_one.append(
            execute_query.submit(conn, plan)
        )

    results_one = {}
    for future in query_futures_one:
        result = future.result()
        results_one.update(result)

    # second second
    query_plans_two = [
        {
            'source': 'addresses',
            'params': {'office_id': results_one['offices']},
        },
        {
            'source': 'parties',
            'columns': ['delivery_address_id', 'mailing_address_id'],
            'params': {'id': results_one['parties']},
            'targets': ['addresses', 'addresses'],
        },
        {
            'source': 'share_series',
            'params': {'share_class_id': results_one['share_classes']},
        },
        {
            'source': 'amalgamating_businesses',
            'params': { 'amalgamation_id': results_one['amalgamations']},
        },
        {
            'source': 'offices_held',
            'params': {'party_role_id': results_one['party_roles']},
        }
    ]

    query_futures_two = []
    for plan in query_plans_two:
        query_futures_two.append(
            execute_query.submit(conn, plan)
        )

    delete_futures = []
    # delete for first query results
    for table, ids in results_one.items():
        delete_futures.append(
            execute_delete_plan.submit(conn, table, ids)
        )
    # delete for second query results
    for future in query_futures_two:
        delete_plans = future.result()
        for table, ids in delete_plans.items():
            delete_futures.append(
                execute_delete_plan.submit(conn, table, ids)
            )

    wait(delete_futures)
    succeeded = sum(1 for f in delete_futures if f.state.is_completed())
    failed = len(delete_futures) - succeeded
    print(f'Lear delete (non-versioned) complete for this round. Succeeded: {succeeded}. Failed: {failed}')


@task
def lear_delete_versioned(conn: Connection, business_ids: list):
    # filing, transaction
            filings_transaction_future = execute_query.submit(conn, {
                'source': 'filings',
                'columns': ['id', 'transaction_id'],
                'params': {'business_id': business_ids},
                'targets': ['filings', 'transaction'],
            })

            plans = filings_transaction_future.result()

            filing_ids = plans['filings']
            transaction_ids = plans['transaction']

            query_plans = [
                # based on transaction_id
                {
                    'source': 'addresses_version',
                    'params': {'transaction_id': transaction_ids},
                },
                {
                    'source': 'aliases_version',
                    'params': {'transaction_id': transaction_ids},
                },
                {
                    'source': 'amalgamating_businesses_version',
                    'params': {'transaction_id': transaction_ids},
                },
                {
                    'source': 'amalgamations_version',
                    'params': {'transaction_id': transaction_ids},
                },
                {
                    'source': 'documents_version',
                    'params': {'transaction_id': transaction_ids},
                },
                {
                    'source': 'jurisdictions_version',
                    'params': {'transaction_id': transaction_ids},
                },
                {
                    'source': 'offices_version',
                    'params': {'transaction_id': transaction_ids},
                },
                {
                    'source': 'parties_version',
                    'params': {'transaction_id': transaction_ids},
                },
                {
                    'source': 'party_roles_version',
                    'params': {'transaction_id': transaction_ids},
                },
                {
                    'source': 'resolutions_version',
                    'params': {'transaction_id': transaction_ids},
                },
                {
                    'source': 'share_classes_version',
                    'params': {'transaction_id': transaction_ids},
                },
                {
                    'source': 'share_series_version',
                    'params': {'transaction_id': transaction_ids},
                },
                {
                    'source': 'offices_held_version',
                    'params': {'transaction_id': transaction_ids},
                },
                # based on others
                {
                    'source': 'batch_processing',
                    'columns': ['id', 'batch_id'],
                    'params': {'business_id': business_ids},
                    'targets': ['batch_processing', 'batches'],
                },
                {
                    'source': 'colin_event_ids',
                    'columns': ['colin_event_id'],
                    'params': {'filing_id': filing_ids},
                },
                {
                    'source': 'comments',
                    'params': {'filing_id': filing_ids},
                },
                {
                    'source': 'furnishings',
                    'params': {'business_id': business_ids},
                },
                # there're some Comment records saved by legal-api directly instead of filer
                # some of them are linked via business_id
                {
                    'source': 'comments',
                    'params': {'business_id': business_ids},
                },
                {
                    'source': 'consent_continuation_outs',
                    'params': {'filing_id': filing_ids},
                },
            ]

            query_futures = []
            for plan in query_plans:
                query_futures.append(
                    execute_query.submit(conn, plan)
                )

            delete_futures = []
            for future in query_futures:
                delete_plans = future.result()
                for table, ids in delete_plans.items():
                    delete_futures.append(
                        execute_delete_plan.submit(conn, table, ids)
                    )

            # the rest of tables
            tables_and_ids = [
                ('businesses', business_ids),
                ('businesses_version', business_ids),
                ('filings', filing_ids),
                ('transaction', transaction_ids)
            ]
            for table, ids in tables_and_ids:
                delete_futures.append(
                    execute_delete_plan.submit(conn, table, ids)
                )

            wait(delete_futures)
            succeeded = sum(1 for f in delete_futures if f.state.is_completed())
            failed = len(delete_futures) - succeeded
            print(f'Lear delete (versioned) complete for this round. Succeeded: {succeeded}. Failed: {failed}')


@task
def lear_delete(db_engine: Engine, business_ids: list):
    with db_engine.connect() as conn:
        with replica_role(conn):
            # no overlaps between versioned & non-versioned records
            versioned = lear_delete_versioned.submit(conn, business_ids)
            non_versioned = lear_delete_non_versioned.submit(conn, business_ids)
            wait([versioned, non_versioned])


@task
def auth_delete(db_engine: Engine, identifiers: list):
    with db_engine.connect() as conn:
        with replica_role(conn):
            entities_future = execute_query.submit(conn, {
                'source': 'entities',
                'params':{'business_identifier': identifiers},
            })

            plan = entities_future.result()

            entity_ids = plan['entities']

            # delete plans for history tables are different from version tables
            # for this versioning method, the first record doesn't exist in history,
            # so we should refer to the original table
            # if the record is deleted in original table, it will be only in history table
            query_plans = [
                {
                    'source': 'affiliations',
                    'params': {'entity_id': entity_ids},
                },
                {
                    'source': 'contact_links',
                    'columns': ['id', 'contact_id'],
                    'params': {'entity_id': entity_ids},
                    'targets': ['contact_links', 'contacts'],
                },
                {
                    'source': 'affiliations_history',
                    'params': {'entity_id': entity_ids},
                },
                {
                    'source': 'contact_links_history',
                    'columns': ['id', 'contact_id'],
                    'params': {'entity_id': entity_ids},
                    'targets': ['contact_links_history', 'contacts_history'],
                }
            ]

            query_futures = []
            for plan in query_plans:
                query_futures.append(
                    execute_query.submit(conn, plan)
                )

            delete_futures = []
            for future in query_futures:
                delete_plans = future.result()
                for table, ids in delete_plans.items():
                    delete_futures.append(
                        execute_delete_plan.submit(conn, table, ids)
                    )

            # delete records in entities table
            delete_futures.append(
                execute_delete_plan.submit(conn, 'entities', entity_ids)
            )

            wait(delete_futures)
            succeeded = sum(1 for f in delete_futures if f.state.is_completed())
            failed = len(delete_futures) - succeeded
            print(f'Auth delete complete for this round. Succeeded: {succeeded}. Failed: {failed}')


@task
def colin_delete(config, db_engine: Engine, identifiers: list):
    with db_engine.connect() as conn:
        with replica_role(conn):
            plan = execute_query(conn, {
                'source': 'corp_processing',
                'params': {'corp_num': identifiers, 'environment': [config.DATA_LOAD_ENV]}
            })

            delete_by_ids(conn, 'corp_processing', plan['corp_processing'])


@task
def auth_api_delete(config, identifiers: list):
    auth_svc_url = config.AUTH_SVC_URL
    account_id = config.AFFILIATE_ENTITY_ACCOUNT_ID
    token_url = config.ACCOUNT_SVC_AUTH_URL
    client_id = config.ACCOUNT_SVC_CLIENT_ID
    client_secret = config.ACCOUNT_SVC_CLIENT_SECRET
    timeout = config.ACCOUNT_SVC_TIMEOUT

    data = 'grant_type=client_credentials'
    res = requests.post(url=token_url,
                        data=data,
                        headers={'content-type': 'application/x-www-form-urlencoded'},
                        auth=(client_id, client_secret),
                        timeout=timeout)
    try:
        token = res.json().get('access_token')
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
        }

        delete_affiliation(identifiers, auth_svc_url, account_id, headers, timeout)
        delete_entities(identifiers, auth_svc_url, headers, timeout)
    except Exception as e:
        print(f'❌ Error deleting affiliations/entities via AUTH API: {repr(e)}')
        raise e


@task
def delete_affiliation(identifiers: list, url, account_id, headers, timeout=None):
    affiliate_url = f'{url}/orgs/{account_id}/affiliations'

    succeeded, failed, skipped = 0, 0, 0
    for id in identifiers:
        res = requests.delete(
            url=f'{affiliate_url}/{id}',
            headers=headers,
            timeout=timeout
        )

        if res.status_code == HTTPStatus.OK:
            succeeded += 1
        elif res.status_code == HTTPStatus.NOT_FOUND:
            skipped += 1
        else:
            failed += 1

    print(f'👷 Auth affiliation delete complete for this round. Succeeded: {succeeded}. Failed: {failed}. Skipped: {skipped}')


@task
def delete_entities(identifiers: list, auth_svc_url, headers, timeout=None):
    account_svc_entity_url = f'{auth_svc_url}/entities'

    succeeded, failed, skipped = 0, 0, 0
    for id in identifiers:
        res = requests.delete(
            url=f'{account_svc_entity_url}/{id}',
            headers=headers,
            timeout=timeout
        )

        if res.status_code == HTTPStatus.NO_CONTENT:
            succeeded += 1
        elif res.status_code == HTTPStatus.NOT_FOUND:
            skipped += 1
        else:
            failed += 1

    print(f'👷 Auth entity delete complete for this round. Succeeded: {succeeded}. Failed: {failed}. Skipped: {skipped}')


def filter_none(values: list) -> list:
    return [v for v in values if v is not None]


@task(persist_result=False)
def execute_query(conn: Connection, template: dict) -> dict:
    """Executes a query based on a structured template.

    :param conn: The database connection object.
    :param template: A dictionary specifying the query structure.

        Expected keys in `template` include:

        - **source** (`str`): The table to query.
        - **columns** (`list[str]`, optional): The columns to select from the `source` table.
          Defaults to `['id']`.
        - **params** (`dict`, optional): A dictionary with filter conditions
          for the query. Defaults to `None`.
        - **targets** (`list[str]`, optional): A list of tables where the results will be mapped
          to targets for delete operations. Defaults to `[source]`.

    :return: A dictionary containing the mapping results. The format is:

        `{ 'target_table_name': [id1, id2, ...] }`

        where each `target_table_name` is a table specified in `targets` or the origin table of a
        `_version` table. The associated value is a list of IDs for records to delete in that table.
    """

    source = template.get('source')
    cols = template.get('columns', ['id'])
    params = template.get('params', None)
    targets = template.get('targets', [source])

    cols_str = ', '.join(cols)
    query = f'SELECT {cols_str} FROM {source} WHERE 1 = 1'

    if params:
        for k, v in params.items():
            if not v:
                query += ' AND 1 != 1'
            else:
                if isinstance(v, str):
                    query += f' AND {k} {v}'
                else:
                    # now only consider str and int in the list
                    v_str = ', '.join(map(lambda x: f'\'{x}\'' if isinstance(x, str) else str(x), filter_none(v)))
                    if v_str:
                        query += f' AND {k} IN ({v_str})'
                    else:
                        query += ' AND 1 != 1'

    results = conn.execute(text(query))

    rows = results.fetchall()
    if not rows:
        # if source table is version table and has no record, then won't generate plan for origin table
        ret = {t: [] for t in targets}
    else:
        cols = zip(*rows)
        ret = defaultdict(list)
        for t, c in zip(targets, cols):
            c = list(c)
            # if source table is version table and has records, will generate plan for origin table
            # update value of key without overriding
            if (origin := (t.rsplit('_version', 1)[0])) != t:
                ret[origin].extend(c)
            ret[t].extend(c)

    return ret


@task(persist_result=False)
def execute_delete_plan(conn: Connection, table: str, ids: list):
    if table == 'colin_event_ids':
        delete_by_ids(conn, table, ids, 'colin_event_id')
    else:
        delete_by_ids(conn, table, ids)


@task(persist_result=False)
def delete_by_ids(conn: Connection, table_name: str, ids: list, id_name: str = 'id'):
    ids = filter_none(ids)
    if ids:
        ids_str = ', '.join(map(lambda x: f'\'{x}\'' if isinstance(x, str) else str(x), ids))
        query_str = f'DELETE FROM {table_name} WHERE {id_name} IN ({ids_str})'
        query = text(query_str)
        results = conn.execute(query, {'ids': ids})
        cnt = results.rowcount
        print(f'Delete {cnt} rows from {table_name}')
    else:
        print(f'Skip deleting {table_name} due to empty ID list')


@task
def count_corp_num(engine: Engine, config):
    with engine.connect() as conn:
        res = conn.execute(text(businesses_cnt_query), {
            'batch_size': config.DELETE_BATCH_SIZE,
            'corp_name_suffix': config.CORP_NAME_SUFFIX
            }).scalar()
        return res


@flow(log_prints=True)
def batch_delete_flow():
    try:
        # init
        config = get_config()
        colin_engine = colin_init(config)
        lear_engine = lear_init(config)
        # use AUTH API for now
        # auth_engine = auth_init(config)

        # get total number of businesses
        total = count_corp_num(lear_engine, config)

        # validate batch config
        if config.DELETE_BATCHES <= 0:
            raise ValueError('DELETE_BATCHES must be explicitly set to a positive integer')
        if config.DELETE_BATCH_SIZE <= 0:
            raise ValueError('DELETE_BATCH_SIZE must be explicitly set to a positive integer')
        batch_size = config.DELETE_BATCH_SIZE
        batches = min(math.ceil(total/batch_size), config.DELETE_BATCHES)

        print(f'👷 Going to delete {total} businesses with batch size of {batch_size}...')
        print(f"👷 Auth delete {'enabled' if config.DELETE_AUTH_RECORDS else 'disabled'}.")

        cnt = 0
        while cnt < batches:
            business_ids, identifiers = get_selected_corps(lear_engine, config)

            if not business_ids:
                break
            print(f'🚀 Running round {cnt} to delete {len(business_ids)} busiesses...')

            futures = []
            futures.append(
                lear_delete.submit(lear_engine, business_ids)
            )
            if config.DELETE_AUTH_RECORDS:
                futures.append(
                    auth_api_delete.submit(config, identifiers)
                )
            if config.DELETE_CORP_PROCESSING_RECORDS:
                futures.append(
                    colin_delete.submit(config, colin_engine, identifiers)
                )

            wait(futures)

            print(f'🌟 Complete round {cnt}')
            rest = count_corp_num(lear_engine, config)
            print(f'👷 Having {rest} businesses left...')
            cnt += 1

        total_left = count_corp_num(lear_engine, config)
        print(f'🌰 Complete {cnt} rounds, delete {total-total_left} businesses.')
    except Exception as e:
        raise e


if __name__ == '__main__':
    batch_delete_flow()
