from typing import List, Dict, Optional

import math
from collections import defaultdict
from contextlib import contextmanager
from http import HTTPStatus

import requests
from common.init_utils import colin_extract_init, get_config, lear_init
from prefect import flow, task
from prefect.cache_policies import NO_CACHE
from prefect.futures import wait
from sqlalchemy import Connection, text, bindparam
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

# MIG account map (aggregated per corp_num); dynamic MIG filters appended by code.
MIG_ACCOUNT_MAP_BASE = """
    SELECT mca.corp_num,
           array_to_string(array_agg(DISTINCT mca.account_id ORDER BY mca.account_id), ',') AS account_ids
    FROM mig_corp_account mca
    JOIN mig_batch b ON b.id = mca.mig_batch_id
    WHERE mca.target_environment = :environment
        AND mca.corp_num IN :corp_nums
        {batch_filter}
        {group_filter}
    GROUP BY mca.corp_num
"""

# corp_processing written by migration (fallback when MIG map/config is empty)
CORP_PROCESSING_ACCOUNTS_BASE = """
    SELECT corp_num, account_ids
    FROM corp_processing
    WHERE flow_name = 'tombstone-flow'
        AND environment = :environment
        AND corp_num IN :corp_nums
        AND COALESCE(NULLIF(account_ids, ''), NULL) IS NOT NULL
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


@task(cache_policy=NO_CACHE)
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


def _parse_accounts_csv(csv_val: str) -> List[int]:
    if not csv_val:
        return []
    out: List[int] = []
    for tok in csv_val.split(','):
        tok = tok.strip()
        if tok.isdigit():
                out.append(int(tok))
    return out


@task(cache_policy=NO_CACHE)
def get_mig_corp_candidates(config, colin_engine: Engine) -> List[str]:
    """
    Build the candidate corp list purely from MIG metadata (COLIN).
    This is used to *replace* suffix-based selection when USE_MIGRATION_FILTER is True.
    """
    if not config.USE_MIGRATION_FILTER:
        return []

    # Parse CSV env strings into integer lists for expanding binds
    batch_ids = _parse_accounts_csv(config.MIG_BATCH_IDS) if config.MIG_BATCH_IDS else []
    group_ids = _parse_accounts_csv(config.MIG_GROUP_IDS) if config.MIG_GROUP_IDS else []

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


@task(cache_policy=NO_CACHE)
def get_affiliation_targets(config, colin_engine: Engine, identifiers: List[str]) -> Dict[str, List[int]]:
    """
    Resolve account IDs per identifier for AUTH affiliation deletion.
    Precedence:
      1) If USE_MIGRATION_FILTER: MIG account map (optional MIG filters)
         If none for a corp, fallback to AFFILIATE_ENTITY_ACCOUNT_IDS.
      2) If not USE_MIGRATION_FILTER: use AFFILIATE_ENTITY_ACCOUNT_IDS (if provided).
      3) Fallback in either case: corp_processing.account_ids (set by migration).
    """
    targets: Dict[str, List[int]] = {i: [] for i in identifiers}
    if not identifiers:
            return targets

    ids_sql_list = ', '.join([f"'{x}'" for x in identifiers])
    env = config.DATA_LOAD_ENV

    # 1) MIG mapping (only when filter is on)
    if config.USE_MIGRATION_FILTER:
        # Parse CSV env strings to lists for safe expanding binds
        batch_ids = _parse_accounts_csv(config.MIG_BATCH_IDS) if config.MIG_BATCH_IDS else []
        group_ids = _parse_accounts_csv(config.MIG_GROUP_IDS) if config.MIG_GROUP_IDS else []

        batch_filter = "AND b.id IN :batch_ids" if batch_ids else ""
        group_filter = "AND b.mig_group_id IN :group_ids" if group_ids else ""
        mig_sql = MIG_ACCOUNT_MAP_BASE.format(
           batch_filter=batch_filter,
           group_filter=group_filter
        )
        stmt = text(mig_sql).bindparams(
        bindparam('environment'),
               bindparam('corp_nums', expanding=True)
        )
        params = {'environment': env, 'corp_nums': identifiers}
        if batch_ids:
           stmt = stmt.bindparams(bindparam('batch_ids', expanding=True))
           params['batch_ids'] = batch_ids
        if group_ids:
           stmt = stmt.bindparams(bindparam('group_ids', expanding=True))
           params['group_ids'] = group_ids

        with colin_engine.connect() as conn:
           rows = conn.execute(stmt, params).fetchall()
           for corp_num, account_ids_csv in rows:
               targets[corp_num] = _parse_accounts_csv(account_ids_csv)

        # Fallback to config accounts for any corp without a MIG map row
        if config.AFFILIATE_ENTITY_ACCOUNT_IDS:
            for i in identifiers:
                if not targets[i]:
                    targets[i] = list(config.AFFILIATE_ENTITY_ACCOUNT_IDS)
    else:
        # No MIG filter → straight to config accounts (if any)
        if config.AFFILIATE_ENTITY_ACCOUNT_IDS:
            for i in identifiers:
                targets[i] = list(config.AFFILIATE_ENTITY_ACCOUNT_IDS)

    # 2) Final fallback: corp_processing (migration cached account_ids CSV)
    remaining = [i for i in identifiers if not targets[i]]
    if remaining:
        cp_sql = CORP_PROCESSING_ACCOUNTS_BASE
        stmt = text(cp_sql).bindparams(bindparam('corp_nums', expanding=True))
        with colin_engine.connect() as conn:
            rows = conn.execute(stmt, {
                'environment': env,
                'corp_nums': remaining
            }).fetchall()
            for corp_num, account_ids_csv in rows:
                if not targets[corp_num]:
                    targets[corp_num] = _parse_accounts_csv(account_ids_csv)

    # Normalize: dedupe/sort
    for i in identifiers:
        if targets[i]:
            targets[i] = sorted(set(targets[i]))
    return targets


@task(cache_policy=NO_CACHE)
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


@task(cache_policy=NO_CACHE)
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


@task(cache_policy=NO_CACHE)
def lear_delete(db_engine: Engine, business_ids: list):
    with db_engine.connect() as conn:
        with replica_role(conn):
            # no overlaps between versioned & non-versioned records
            versioned = lear_delete_versioned.submit(conn, business_ids)
            non_versioned = lear_delete_non_versioned.submit(conn, business_ids)
            wait([versioned, non_versioned])


@task(cache_policy=NO_CACHE)
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


@task(cache_policy=NO_CACHE)
def colin_delete(config, db_engine: Engine, identifiers: list):
    with db_engine.connect() as conn:
        with replica_role(conn):
            plan = execute_query(conn, {
                'source': 'corp_processing',
                'params': {'corp_num': identifiers, 'environment': [config.DATA_LOAD_ENV]}
            })

            delete_by_ids(conn, 'corp_processing', plan['corp_processing'])


@task
def auth_api_delete(config, identifiers: List[str], id_to_accounts: Dict[str, List[int]]):
    auth_svc_url = config.AUTH_SVC_URL
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

        # 1) Delete affiliations (only if AFFILIATE_ENTITY is enabled)
        aff_succeeded = 0
        aff_failed = 0
        aff_skipped = 0
        if config.AFFILIATE_ENTITY and id_to_accounts:
            for identifier, accounts in id_to_accounts.items():
               if not accounts:
                   aff_skipped += 1
                   continue
               for account_id in accounts:
                   affiliate_url = f'{auth_svc_url}/orgs/{account_id}/affiliations/{identifier}'
                   resp = requests.delete(url=affiliate_url, headers=headers, timeout=timeout)
                   if resp.status_code == HTTPStatus.OK:
                       aff_succeeded += 1
                   elif resp.status_code == HTTPStatus.NOT_FOUND:
                       aff_skipped += 1
                   else:
                       aff_failed += 1
        print(f'👷 Auth affiliation delete complete. Succeeded: {aff_succeeded}. Failed: {aff_failed}. Skipped: {aff_skipped}')

        # 2) Delete entities (always when DELETE_AUTH_RECORDS is set by caller)
        ent_succeeded = 0
        ent_failed = 0
        ent_skipped = 0
        entity_base = f'{auth_svc_url}/entities'
        for identifier in identifiers:
            resp = requests.delete(url=f'{entity_base}/{identifier}', headers=headers, timeout=timeout)
            if resp.status_code == HTTPStatus.NO_CONTENT:
                ent_succeeded += 1
            elif resp.status_code == HTTPStatus.NOT_FOUND:
                ent_skipped += 1
            else:
                ent_failed += 1
        print(f'👷 Auth entity delete complete. Succeeded: {ent_succeeded}. Failed: {ent_failed}. Skipped: {ent_skipped}')
    except Exception as e:
        print(f'❌ Error deleting affiliations/entities via AUTH API: {repr(e)}')
        raise e

def filter_none(values: list) -> list:
    return [v for v in values if v is not None]


@task(persist_result=False, cache_policy=NO_CACHE)
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


@task(persist_result=False, cache_policy=NO_CACHE)
def execute_delete_plan(conn: Connection, table: str, ids: list):
    if table == 'colin_event_ids':
        delete_by_ids(conn, table, ids, 'colin_event_id')
    else:
        delete_by_ids(conn, table, ids)


@task(persist_result=False, cache_policy=NO_CACHE)
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


@task(cache_policy=NO_CACHE)
def count_corp_num(engine: Engine, config, mig_candidates: Optional[List[str]] = None):
    """
    Returns the total to process.
      - MIG mode (USE_MIGRATION_FILTER=True): return len(mig_candidates) and do NOT query LEAR.
      - Non-MIG mode: use the existing suffix-based LEAR count query.
    """
    if config.USE_MIGRATION_FILTER and mig_candidates is not None:
        return len(mig_candidates)
    with engine.connect() as conn:
        res = conn.execute(
            text(businesses_cnt_query),
            {'corp_name_suffix': config.CORP_NAME_SUFFIX}
        ).scalar()
        return res


@task(cache_policy=NO_CACHE)
def get_selected_corps_mig(db_engine: Engine, config, candidates: List[str], offset: int):
    """
    MIG mode selection: page the MIG candidate list in memory and map to LEAR IDs.
    Skips empty slices (where none of the identifiers exist in this LEAR env).
    Does NOT use identifiers_query.
    """
    batch_size = config.DELETE_BATCH_SIZE
    n = len(candidates)
    sql = text("SELECT id, identifier FROM businesses WHERE identifier IN :ids") \
               .bindparams(bindparam('ids', expanding=True))
    curr = offset
    with db_engine.connect() as conn:
        while curr < n:
            slice_ids = candidates[curr: curr + batch_size]
            if not slice_ids:
                break
            rows = conn.execute(sql, {'ids': slice_ids}).fetchall()
            curr += batch_size  # advance by one page
            if rows:
                ids, identifiers = zip(*rows)
                return list(ids), list(identifiers), curr
    # nothing found in remaining pages
    return None, None, curr

@flow(log_prints=True)
def batch_delete_flow():
    try:
        # init
        config = get_config()
        colin_engine = colin_extract_init(config)
        lear_engine = lear_init(config)
        # use AUTH API for now
        # auth_engine = auth_init(config)

        # Determine mode and build MIG candidates when requested.
        mig_mode = bool(config.USE_MIGRATION_FILTER)
        mig_corp_candidates: List[str] = []
        if mig_mode:
            mig_corp_candidates = get_mig_corp_candidates(config, colin_engine)

        # Total to process:
        total = count_corp_num(lear_engine, config, mig_candidates=mig_corp_candidates if mig_mode else None)

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
        mig_offset = 0
        while cnt < batches:
            if mig_mode:
                    business_ids, identifiers, mig_offset = get_selected_corps_mig(lear_engine, config, mig_corp_candidates, mig_offset)
            else:
                business_ids, identifiers = get_selected_corps(lear_engine, config)

            if not business_ids:
                break
            print(f'🚀 Running round {cnt} to delete {len(business_ids)} busiesses...')

            futures = []
            futures.append(lear_delete.submit(lear_engine, business_ids))

            if config.DELETE_AUTH_RECORDS:
                id_to_accounts: Dict[str, List[int]] = (
                    get_affiliation_targets(config, colin_engine, identifiers)
                    if config.AFFILIATE_ENTITY else {}
                )
                futures.append(auth_api_delete.submit(config, identifiers, id_to_accounts))

            if config.DELETE_CORP_PROCESSING_RECORDS:
                futures.append(colin_delete.submit(config, colin_engine, identifiers))

            wait(futures)

            print(f'🌟 Complete round {cnt}')
            if mig_mode:
                rest = max(len(mig_corp_candidates) - mig_offset, 0)
            else:
                rest = count_corp_num(lear_engine, config)
            print(f'👷 Having {rest} businesses left...')
            cnt += 1

            if mig_mode:
                    total_left = max(len(mig_corp_candidates) - mig_offset, 0)
            else:
                total_left = count_corp_num(lear_engine, config)
            print(f'🌰 Complete {cnt} rounds, delete {total - total_left} businesses.')
    except Exception as e:
        raise e


if __name__ == '__main__':
    batch_delete_flow()
