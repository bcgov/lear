import time

from prefect import flow, task
from common.init_utils import colin_extract_init, colin_oracle_init, get_config
from common.colin_utils import colin_oracle_chunks
from sqlalchemy import Engine, text
from prefect.task_runners import ConcurrentTaskRunner

from prefect.cache_policies import NO_CACHE
from prefect.context import get_run_context
from prefect.states import Failed

from common.extract_tracking_service \
    import ExtractTrackingService as ColinTrackingService, ProcessingStatuses

FLOW_NAME = 'colin-freeze-flow'
ORACLE_IN_LIMIT = 1000
DEFAULT_ORACLE_CHUNK_SIZE = 1000

colin_freeze_select_query = """
SELECT c.corp_num
FROM corporation c
WHERE c.corp_num IN {corp_nums}
"""

colin_freeze_query = """
UPDATE corporation c
SET corp_frozen_typ_cd = 'C'
WHERE c.corp_num IN {corp_nums}
"""

colin_add_early_adopters_query = """
MERGE INTO corp_early_adopters cea
USING (SELECT :corp_num AS corp_num FROM dual) src
ON (cea.corp_num = src.corp_num)
WHEN NOT MATCHED THEN
    INSERT (corp_num, start_date)
    VALUES (src.corp_num, SYSDATE)
"""


def get_incomplete_count_query(flow_name, environment):
    query = f"""
    SELECT COUNT(*) FROM corporation c
    LEFT JOIN colin_tracking ct
    ON ct.corp_num = c.corp_num
    AND ct.flow_name = '{flow_name}'
    AND ct.environment = '{environment}'
    WHERE 1 = 1
    AND (ct.processed_status is null OR ct.processed_status != 'COMPLETED')
    AND ct.flow_run_id is null
    """
    return query


@task(cache_policy=NO_CACHE)
def get_incomplete_count(config, colin_extract_engine: Engine) -> int:
    query = get_incomplete_count_query(
        FLOW_NAME,
        config.DATA_LOAD_ENV
    )

    with colin_extract_engine.connect() as conn:
        total = conn.execute(text(query)).scalar()
        return total


def get_onboarding_group_subquery():
    # Note: we can typically use the migration filter + migration table entries to determine which groups + batches
    # we want to filter on.  But there may still be one off scenarios where we want to freeze specific corps
    # based off of a one off query.  This can be done here if required.
    return '', ''


def get_unprocessed_corps_query(flow_name, config, batch_size):
    environment = config.DATA_LOAD_ENV
    use_mig_filter = config.USE_MIGRATION_FILTER
    mig_group_ids  = config.MIG_GROUP_IDS
    mig_batch_ids  = config.MIG_BATCH_IDS

    cte_clause, where_clause = get_onboarding_group_subquery()

    if use_mig_filter:
        mig_extra = ""
        if mig_batch_ids:
            mig_extra += f" AND b.id IN ({mig_batch_ids})"
        if mig_group_ids:
            mig_extra += f" AND g.id IN ({mig_group_ids})"

        # Drive migration-filtered freeze reservations from the migration batch table.
        # When a batch is partially processed, starting from corporation can scan large
        # portions of the extract before finding the remaining untracked batch members.
        query = f"""
        {cte_clause}
        SELECT c.corp_num,
               b.id AS mig_batch_id,
               c.corp_type_cd
        FROM mig_corp_batch mcb
        JOIN mig_batch b ON b.id = mcb.mig_batch_id
        JOIN mig_group g ON g.id = b.mig_group_id
        JOIN corporation c ON c.corp_num = mcb.corp_num
        LEFT JOIN colin_tracking ct
        ON ct.corp_num = c.corp_num
        AND ct.flow_name = '{flow_name}'
        AND ct.environment = '{environment}'
        WHERE 1 = 1
        {where_clause} {mig_extra}
        AND ct.corp_num IS NULL
        LIMIT {batch_size}
        """
        return query

    query = f"""
    {cte_clause}
    SELECT c.corp_num,
           NULL::integer AS mig_batch_id,
           c.corp_type_cd 
    FROM corporation c
    LEFT JOIN colin_tracking ct
    ON ct.corp_num = c.corp_num
    AND ct.flow_name = '{flow_name}'
    AND ct.environment = '{environment}'z
    WHERE 1 = 1
    {where_clause}
    AND ct.corp_num IS NULL
    LIMIT {batch_size}
    """
    return query


# TODO: Refactor after group & batch info is ready
# It can be refactored into service method,
# or can be just updated with more parameters for selection query
@task(cache_policy=NO_CACHE)
def reserve_unprocessed_corps(config, processing_service, flow_run_id, num_corps) -> int:
    """Reserve corps for a given flow run and return the number of rows reserved.

    Note that this is not same as claiming them for processing which will be done in some subsequent steps.  This step
    is done to avoid parallel flows from trying to compete for the same corps.
    """
    base_query = get_unprocessed_corps_query(
        FLOW_NAME,
        config,
        num_corps  # Pass the total number we want to process
    )

    # reserve corps
    reserved = processing_service.reserve_for_flow(base_query, flow_run_id)
    return reserved


def convert_to_colin_format(corp_num: str) -> str:
    if corp_num.startswith('BC'):
        return corp_num[2:]
    return corp_num


def chunk_list(values: list[str], size: int) -> list[list[str]]:
    """Split values into ordered chunks."""
    return colin_oracle_chunks(values, size)


def build_in_bind_clause(values: list[str], prefix: str = 'corp') -> tuple[str, dict]:
    """Build a bound Oracle IN-list clause and params for the provided values."""
    params = {f'{prefix}_{i}': value for i, value in enumerate(values)}
    clause = '(' + ', '.join(f':{name}' for name in params) + ')'
    return clause, params


def record_oracle_results(
    colin_tracking_service,
    flow_run_id: str,
    results: list[tuple[str, bool, bool, Exception | None]],
) -> tuple[int, int]:
    """Record one tracking status update for each Oracle result tuple."""
    complete = 0
    failed = 0
    for corp_num, frozen, in_early_adopter, error in results:
        if error:
            failed += 1
            colin_tracking_service.update_corp_status(
                flow_run_id,
                corp_num,
                ProcessingStatuses.FAILED,
                repr(error),
                frozen=frozen,
                in_early_adopter=in_early_adopter
            )
        else:
            complete += 1
            colin_tracking_service.update_corp_status(
                flow_run_id,
                corp_num,
                ProcessingStatuses.COMPLETED,
                error=None,
                frozen=frozen,
                in_early_adopter=in_early_adopter
            )
    return complete, failed


def get_freeze_reservation_limit(config) -> int:
    """Return the configured maximum number of corps to reserve for a freeze run."""
    return config.FREEZE_BATCHES * config.FREEZE_BATCH_SIZE


def get_reserved_batch_count(reserved_corps: int, batch_size: int, max_batches: int) -> int:
    """Return how many claim/processing rounds are needed for the actual reserved count."""
    if reserved_corps <= 0:
        return 0
    return min((reserved_corps + batch_size - 1) // batch_size, max_batches)


def get_reservation_statement_timeout_ms(config) -> int:
    """Require a Postgres statement timeout for the reservation query."""
    timeout_ms = getattr(config, 'RESERVE_STATEMENT_TIMEOUT_MS', None)
    if timeout_ms is None or timeout_ms <= 0:
        raise ValueError('RESERVE_STATEMENT_TIMEOUT_MS must be set to a positive integer for colin freeze reservation')
    return timeout_ms


@task(cache_policy=NO_CACHE)
def update_colin_oracle_chunk(config, colin_oracle_engine: Engine, corp_nums: list[str]):
    if not corp_nums:
        return []

    if len(corp_nums) > ORACLE_IN_LIMIT:
        error = ValueError(f'Chunk size {len(corp_nums)} exceeds ORACLE_IN_LIMIT {ORACLE_IN_LIMIT}')
        return [(corp_num, False, False, error) for corp_num in corp_nums]

    if not config.FREEZE_COLIN_CORPS and not config.FREEZE_ADD_EARLY_ADOPTER:
        return [(corp_num, False, False, None) for corp_num in corp_nums]

    task_start = time.monotonic()
    last_step = task_start

    def mark_step(step_name: str):
        nonlocal last_step
        now = time.monotonic()
        print(
            f'⏱️ Oracle freeze chunk {step_name}: '
            f'{now - last_step:.2f}s since previous step, {now - task_start:.2f}s total'
        )
        last_step = now

    print(
        f'👷 Oracle freeze chunk starting for {len(corp_nums)} corps '
        f'({corp_nums[:5]}), Freeze={config.FREEZE_COLIN_CORPS}, '
        f'EarlyAdopter={config.FREEZE_ADD_EARLY_ADOPTER}'
    )

    colin_corp_num_list = [convert_to_colin_format(corp_num) for corp_num in corp_nums]
    in_clause, in_params = build_in_bind_clause(colin_corp_num_list)
    frozen_colin_nums = set()

    def failed_results(error):
        mark_step('returning failed results')
        return [
            (
                corp_num,
                False,
                False,
                error,
            )
            for corp_num in corp_nums
        ]

    try:
        print(f'👷 Oracle connection checkout starting for {len(corp_nums)} corps ({corp_nums[:5]})')
        with colin_oracle_engine.connect() as conn:
            mark_step('connection acquired')
            transaction = None
            try:
                print(f'👷 Oracle transaction begin starting for {len(corp_nums)} corps ({corp_nums[:5]})')
                transaction = conn.begin()
                mark_step('transaction began')

                if config.FREEZE_COLIN_CORPS:
                    print(f'👷 Oracle freeze preselect starting for {len(corp_nums)} corps ({corp_nums[:5]})')
                    result = conn.execute(
                        text(colin_freeze_select_query.format(corp_nums=in_clause)),
                        in_params
                    )
                    frozen_colin_nums = {row[0] for row in result.fetchall()}
                    mark_step(f'freeze preselect matched {len(frozen_colin_nums)} corps')

                    print(f'👷 Oracle freeze update starting for {len(corp_nums)} corps ({corp_nums[:5]})')
                    conn.execute(
                        text(colin_freeze_query.format(corp_nums=in_clause)),
                        in_params
                    )
                    mark_step('freeze update completed')

                if config.FREEZE_ADD_EARLY_ADOPTER:
                    print(f'👷 Oracle early-adopter MERGE starting for {len(corp_nums)} corps ({corp_nums[:5]})')
                    conn.execute(
                        text(colin_add_early_adopters_query),
                        [{'corp_num': corp_num} for corp_num in colin_corp_num_list]
                    )
                    mark_step('early-adopter MERGE completed')

                print(f'👷 Oracle commit starting for {len(corp_nums)} corps ({corp_nums[:5]})')
                transaction.commit()
                transaction = None
                mark_step('commit completed')
            except Exception as e:  # pylint: disable=broad-exception-caught
                print(f'❌ Oracle chunk error for {len(corp_nums)} corps ({corp_nums[:5]}): {repr(e)}')
                if transaction is not None:
                    rollback_start = time.monotonic()
                    try:
                        transaction.rollback()
                        print(
                            f'⏱️ Oracle rollback completed for {len(corp_nums)} corps '
                            f'in {time.monotonic() - rollback_start:.2f}s'
                        )
                    except Exception as rollback_error:  # pylint: disable=broad-exception-caught
                        print(
                            f'❌ Oracle rollback failed for {len(corp_nums)} corps '
                            f'({corp_nums[:5]}): {repr(rollback_error)}'
                        )
                return failed_results(e)
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f'❌ Oracle connection/context error for {len(corp_nums)} corps ({corp_nums[:5]}): {repr(e)}')
        return failed_results(e)

    results = []
    for original_corp_num, colin_corp_num in zip(corp_nums, colin_corp_num_list):
        frozen = colin_corp_num in frozen_colin_nums if config.FREEZE_COLIN_CORPS else False
        in_early_adopter = config.FREEZE_ADD_EARLY_ADOPTER
        results.append((original_corp_num, frozen, in_early_adopter, None))
    mark_step('returning successful results')
    return results


# Backwards-compatible task symbol for older imports/tests.
update_colin_oracle = update_colin_oracle_chunk


@flow(
    name='Colin-Freeze-Flow',
    task_runner=ConcurrentTaskRunner(max_workers=10),
    log_prints=True,
)
def colin_freeze_flow():
    try:
        config = get_config()
        colin_oracle_engine = colin_oracle_init(config)
        colin_extract_engine = colin_extract_init(config)
        oracle_chunk_size = getattr(config, 'FREEZE_ORACLE_CHUNK_SIZE', DEFAULT_ORACLE_CHUNK_SIZE)
        if oracle_chunk_size < 1 or oracle_chunk_size > ORACLE_IN_LIMIT:
            raise ValueError(f'FREEZE_ORACLE_CHUNK_SIZE must be between 1 and {ORACLE_IN_LIMIT}')

        if config.FREEZE_BATCHES <= 0:
            raise ValueError('FREEZE_BATCHES must be explicitly set to a positive integer')
        if config.FREEZE_BATCH_SIZE <= 0:
            raise ValueError('FREEZE_BATCH_SIZE must be explicitly set to a positive integer')
        batch_size = config.FREEZE_BATCH_SIZE
        max_num = get_freeze_reservation_limit(config)
        reservation_timeout_ms = get_reservation_statement_timeout_ms(config)

        flow_run_id = get_run_context().flow_run.id
        colin_tracking_service = ColinTrackingService(
            config.DATA_LOAD_ENV,
            colin_extract_engine,
            FLOW_NAME,
            'colin_tracking',
            statement_timeout_ms=reservation_timeout_ms
        )
        print(
            f'👷 Preparing to reserve up to {max_num} corps for freeze flow. '
            f'Batches={config.FREEZE_BATCHES}, BatchSize={batch_size}, '
            f'Env={config.DATA_LOAD_ENV}, UseMigrationFilter={config.USE_MIGRATION_FILTER}, '
            f'MigGroupIds={config.MIG_GROUP_IDS or "(none)"}, '
            f'MigBatchIds={config.MIG_BATCH_IDS or "(none)"}, '
            f'ReserveStatementTimeoutMs={reservation_timeout_ms}'
        )
        reserved_corps = reserve_unprocessed_corps(config, colin_tracking_service, flow_run_id, max_num)
        print(f'👷 Reserved {reserved_corps} corps for processing')
        batches = get_reserved_batch_count(reserved_corps, batch_size, config.FREEZE_BATCHES)
        if batches <= 0:
            print('No reservable corps found for this run (cohort may be exhausted or already reserved).')
            return
        print(f'👷 Going to update(freeze) corps in colin before migration with batch size of {batch_size}.')
        print(f'👷 [1] Freeze={config.FREEZE_COLIN_CORPS}')
        print(f'👷 [2] Add into corp_early_adopters table={config.FREEZE_ADD_EARLY_ADOPTER}.')

        cnt = 0
        total_failed = 0
        total_frozen = 0
        while cnt < batches:
            corp_nums = colin_tracking_service.claim_batch(
                flow_run_id, batch_size)

            if not corp_nums:
                print("No more corps available to claim")
                break

            print(f'👷 Start processing {len(corp_nums)} corps: {", ".join(corp_nums[:5])}...')

            futures = []
            for corp_chunk in chunk_list(corp_nums, oracle_chunk_size):
                futures.append((
                    corp_chunk,
                    update_colin_oracle_chunk.submit(
                        config, colin_oracle_engine, corp_chunk)
                ))
            complete = 0
            failed = 0
            for corp_chunk, future in futures:
                wait_start = time.monotonic()
                print(f'👷 Waiting for Oracle chunk of {len(corp_chunk)} corps ({corp_chunk[:5]})')
                results = future.result()
                print(
                    f'⏱️ Oracle chunk future returned for {len(corp_chunk)} corps '
                    f'in {time.monotonic() - wait_start:.2f}s'
                )
                chunk_complete, chunk_failed = record_oracle_results(
                    colin_tracking_service,
                    flow_run_id,
                    results
                )
                print(
                    f'👷 Recorded Oracle chunk results for {len(corp_chunk)} corps: '
                    f'Complete={chunk_complete}, Failed={chunk_failed}'
                )
                complete += chunk_complete
                failed += chunk_failed

            total_failed += failed
            cnt += 1
            total_frozen += complete
            print(f'🌟 Complete round {cnt}. Complete: {complete}. Failed: {failed}.')

        print(f'🌰 Complete {cnt} rounds, update {total_frozen} corps in colin.')

        if total_failed > 0:
            return Failed(message=f'{total_failed} corps failed to update in colin.')

    except Exception as e:
        raise e


if __name__ == '__main__':
    colin_freeze_flow()
