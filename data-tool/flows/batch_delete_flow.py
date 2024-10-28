import math
from contextlib import contextmanager

from config import get_named_config
from prefect import flow, task
from prefect.futures import wait
from sqlalchemy import Connection, create_engine, exc, text
from sqlalchemy.engine import Engine


businesses_cnt_query = """
SELECT COUNT(*) FROM businesses
"""

identifiers_query = """
SELECT id, identifier FROM businesses
-- WHERE legal_type IN ('BC', 'ULC', 'CC')
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
    finally:
        conn.execute(text("SET session_replication_role = 'origin';"))


@task
def get_config():
    config = get_named_config()
    return config

@task
def check_db_connection(db_engine: Engine):
    with db_engine.connect() as conn:
        res = conn.execute(text('SELECT current_database()')).scalar()
        if not res:
            raise ValueError("Failed to retrieve the current database name.")
        print(f'✅ Connected to database: {res}')



@task
def colin_init(config):
    try:
        engine = create_engine(config.SQLALCHEMY_DATABASE_URI_COLIN_MIGR)
        check_db_connection(engine)
        return engine
    except Exception as e:
        raise Exception('Failed to create engine for COLIN DB') from e


@task
def lear_init(config):
    try:
        engine = create_engine(
            config.SQLALCHEMY_DATABASE_URI,
            **config.SQLALCHEMY_ENGINE_OPTIONS
        )
        check_db_connection(engine)
        return engine
    except Exception as e:
        raise Exception('Failed to create engine for LEAR DB') from e


@task
def auth_init(config):
    try:
        engine = create_engine(config.SQLALCHEMY_DATABASE_URI_AUTH)
        check_db_connection(engine)
        return engine
    except Exception as e:
        raise Exception('Failed to create engine for AUTH DB') from e


@task
def get_selected_corps(db_engine: Engine, config):
    with db_engine.connect() as conn:
        results = conn.execute(text(identifiers_query), {'batch_size': config.BATCH_SIZE})
        rows = results.fetchall()

        if not rows:
            return None, None
        else:
            ids, identifiers = zip(*rows)
            return list(ids), list(identifiers)


@task
def lear_delete(db_engine: Engine, business_ids: list):
    with db_engine.connect() as conn:
        with replica_role(conn):
            # filing, transaction
            filings_transaction_future = execute_query.submit(conn, {
                'source': 'filings',
                'columns': ['id', 'transaction_id'],
                'params': {'transaction_id': 'IS NOT NULL', 'business_id': business_ids},
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
                # there're some Comment records saved by legal-api directly instead of filer
                # should ignore them (assume that it won't be populated with migrated data)
                {
                    'source': 'comments',
                    'params': {'filing_id': filing_ids},
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
            print(f'Lear delete complete for this round. Succeeded: {succeeded}. Failed: {failed}')


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
        plan = execute_query(conn, {
            'source': 'corp_processing',
            'params': {'corp_num': identifiers, 'environment': [config.DATA_LOAD_ENV]}
        })

        delete_by_ids(conn, 'corp_processing', plan['corp_processing'])


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
                    v_str = ', '.join(map(lambda x: f'\'{x}\'' if isinstance(x, str) else str(x), v))
                    query += f' AND {k} IN ({v_str})'

    results = conn.execute(text(query))

    rows = results.fetchall()
    if not rows:
        # if source table is version table and has no record, then won't generate plan for origin table
        ret = {t: [] for t in targets}
    else:   
        cols = zip(*rows)
        ret = {}
        for t, c in zip(targets, cols):
            c = list(c)
            # if source table is version table and has records, will generate plan for origin table
            if (origin := (t.rsplit('_version', 1)[0])) != t:
                ret[origin] = c
            ret[t] = c
    
    return ret


@task(persist_result=False)
def execute_delete_plan(conn: Connection, table: str, ids: list):
    if table == 'colin_event_ids':
        delete_by_ids(conn, table, ids, 'colin_event_id')
    else:
        delete_by_ids(conn, table, ids)


@task(persist_result=False)
def delete_by_ids(conn: Connection, table_name: str, ids: list, id_name: str = 'id'):
    if ids:
        ids_str = ', '.join(map(lambda x: f'\'{x}\'' if isinstance(x, str) else str(x), ids))
        query_str = f'DELETE FROM {table_name} WHERE {id_name} IN ({ids_str})'
        query = text(query_str)
        results = conn.execute(query, {'ids': ids})
        cnt = results.rowcount
        print(f'Delete {cnt} rows from {table_name}')
    else:
        print(f'Skip deleting {table_name} table due to empty list')


@task
def count_corp_num(engine: Engine):
    with engine.connect() as conn:
        res = conn.execute(text(businesses_cnt_query)).scalar()
        return res


@flow(log_prints=True)
def batch_delete_flow():
    try:
        # init
        config = get_config()
        colin_engine = colin_init(config)
        lear_engine = lear_init(config)
        auth_engine = auth_init(config)

        # get total number of businesses, batches
        total = count_corp_num(lear_engine)
        batch_size = config.BATCH_SIZE
        batches = min(math.ceil(total/batch_size), config.BATCHES)

        print(f'👷 Going to delete {total} businesses with batch size of {batch_size}...')
        print(f"👷 Auth delete {'enabled' if config.DELETE_AUTH_RECORDS else 'disabled'}.")

        cnt = 0
        while cnt < batches:
            business_ids, identifiers = get_selected_corps(lear_engine, config)

            if not business_ids:
                break
            print(f'🚀 Running round {cnt} to delete {len(business_ids)} busiesses...')

            db_futures = []
            db_futures.append(
                lear_delete.submit(lear_engine, business_ids)
            )
            if config.DELETE_AUTH_RECORDS:
                db_futures.append(
                    auth_delete.submit(auth_engine, identifiers)
                )
            if config.DELETE_COLIN_RECORDS:
                db_futures.append(
                    colin_delete.submit(config, colin_engine, identifiers)
                )

            wait(db_futures)

            print(f'🌟 Complete round {cnt}')
            rest = count_corp_num(lear_engine)
            print(f'👷 Having {rest} businesses left...')
            cnt += 1

        print(f'🌰 Complete {cnt} rounds, delete {total} businesses.')
    except Exception as e:
        raise e


if __name__ == '__main__':
    batch_delete_flow()
