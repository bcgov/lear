import math
from prefect import flow, task
from common.init_utils import colin_extract_init, colin_oracle_init, get_config
from sqlalchemy import Engine, text

from prefect.cache_policies import NO_CACHE
from prefect.context import get_run_context
from prefect.states import Failed

from common.extract_tracking_service \
    import ExtractTrackingService as ColinTrackingService, ProcessingStatuses

FLOW_NAME = 'colin-freeze-flow'
ORACLE_IN_LIMIT = 1000
DEFAULT_ORACLE_CHUNK_SIZE = 1000


colin_freeze_query = """
UPDATE corporation c
SET corp_frozen_typ_cd = 'C'
WHERE c.corp_num = :corp_num
"""

colin_add_early_adopters_query = """
INSERT INTO corp_early_adopters(corp_num, start_date)
VALUES (:corp_num, SYSDATE)
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
    mig_group_ids = config.MIG_GROUP_IDS
    mig_batch_ids = config.MIG_BATCH_IDS

    cte_clause, where_clause = get_onboarding_group_subquery()

    if use_mig_filter:
        mig_select = "b.id AS mig_batch_id,"
        mig_join = """
            JOIN mig_corp_batch mcb ON mcb.corp_num = c.corp_num
            JOIN mig_batch            b  ON b.id        = mcb.mig_batch_id
            JOIN mig_group            g  ON g.id        = b.mig_group_id
            """
        mig_extra = ""
        if mig_batch_ids:
            mig_extra += f" AND b.id IN ({mig_batch_ids})"
        if mig_group_ids:
            mig_extra += f" AND g.id IN ({mig_group_ids})"
    else:
        mig_select = "NULL::integer AS mig_batch_id,"
        mig_join = ""
        mig_extra = ""

    query = f"""
    {cte_clause}
    SELECT c.corp_num,
           {mig_select} 
           c.corp_type_cd 
    FROM corporation c
    {mig_join}
    LEFT JOIN colin_tracking ct
    ON ct.corp_num = c.corp_num
    AND ct.flow_name = '{flow_name}'
    AND ct.environment = '{environment}'
    WHERE 1 = 1
    {where_clause} {mig_extra}
    AND ct.processed_status is null
    AND ct.flow_run_id is null
    LIMIT {batch_size}
    """
    return query


# TODO: Refactor after group & batch info is ready
# It can be refactored into service method,
# or can be just updated with more parameters for selection query
@task(cache_policy=NO_CACHE)
def reserve_unprocessed_corps(config, processing_service, flow_run_id, num_corps) -> list:
    """Reserve corps for a given flow run.

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
    return [values[i:i + size] for i in range(0, len(values), size)]


def build_in_bind_clause(values: list[str], prefix: str = 'corp') -> tuple[str, dict]:
    bind_names = [f'{prefix}_{i}' for i in range(len(values))]
    clause = f"({', '.join(f':{name}' for name in bind_names)})"
    params = {name: value for name, value in zip(bind_names, values)}
    return clause, params


@task(cache_policy=NO_CACHE)
def update_colin_oracle_chunk(config, colin_oracle_engine: Engine, corp_nums: list[str]):
    if not corp_nums:
        return []

    if len(corp_nums) > ORACLE_IN_LIMIT:
        error = ValueError(f'Chunk size {len(corp_nums)} exceeds ORACLE_IN_LIMIT {ORACLE_IN_LIMIT}')
        return [(corp_num, False, False, error) for corp_num in corp_nums]

    if not config.FREEZE_COLIN_CORPS and not config.FREEZE_ADD_EARLY_ADOPTER:
        return [(corp_num, False, False, None) for corp_num in corp_nums]

    colin_corp_nums = [convert_to_colin_format(corp_num) for corp_num in corp_nums]
    in_clause, in_params = build_in_bind_clause(colin_corp_nums)

    with colin_oracle_engine.connect() as conn:
        transaction = conn.begin()
        frozen_colin_nums = set()
        try:
            if config.FREEZE_COLIN_CORPS:
                select_query = f"""
                SELECT c.corp_num
                FROM corporation c
                WHERE c.corp_num IN {in_clause}
                """
                rows = conn.execute(text(select_query), in_params).fetchall()
                frozen_colin_nums = {row[0] for row in rows}

                freeze_query = f"""
                UPDATE corporation c
                SET corp_frozen_typ_cd = 'C'
                WHERE c.corp_num IN {in_clause}
                """
                conn.execute(text(freeze_query), in_params)

            if config.FREEZE_ADD_EARLY_ADOPTER:
                early_adopter_params = [{'corp_num': corp_num} for corp_num in colin_corp_nums]
                conn.execute(text(colin_add_early_adopters_query), early_adopter_params)
        except Exception as e:
            print(f'❌ Chunk statement error for {len(corp_nums)} corps ({corp_nums[:5]}): {repr(e)}')
            try:
                transaction.commit()
                print(f'⚠️ Chunk statement-error-path commit succeeded for {len(corp_nums)} corps ({corp_nums[:5]})')
            except Exception as commit_error:
                print(f'❌ Chunk statement-error-path commit failed for {len(corp_nums)} corps ({corp_nums[:5]}): {repr(commit_error)}')
            return [
                (
                    corp_num,
                    convert_to_colin_format(corp_num) in frozen_colin_nums if config.FREEZE_COLIN_CORPS else False,
                    False,
                    e,
                )
                for corp_num in corp_nums
            ]

        try:
            transaction.commit()
        except Exception as e:
            print(f'❌ Chunk commit error for {len(corp_nums)} corps ({corp_nums[:5]}): {repr(e)}')
            return [(corp_num, False, False, e) for corp_num in corp_nums]

        results = []
        for original_corp_num, colin_corp_num in zip(corp_nums, colin_corp_nums):
            frozen = colin_corp_num in frozen_colin_nums if config.FREEZE_COLIN_CORPS else False
            in_early_adopter = config.FREEZE_ADD_EARLY_ADOPTER
            results.append((original_corp_num, frozen, in_early_adopter, None))
        return results


def record_oracle_results(colin_tracking_service, flow_run_id: str, results: list[tuple]):
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


@flow(
    name='Colin-Freeze-Flow',
    log_prints=True,
)
def colin_freeze_flow():
    try:
        config = get_config()
        colin_oracle_engine = colin_oracle_init(config)
        colin_extract_engine = colin_extract_init(config)

        total = get_incomplete_count(config, colin_extract_engine)
        print(f'👷 Statistics: {total} incomplete corps (unprocessed or failed)')

        if config.FREEZE_BATCHES <= 0:
            raise ValueError('FREEZE_BATCHES must be explicitly set to a positive integer')
        if config.FREEZE_BATCH_SIZE <= 0:
            raise ValueError('FREEZE_BATCH_SIZE must be explicitly set to a positive integer')

        oracle_chunk_size = getattr(config, 'FREEZE_ORACLE_CHUNK_SIZE', DEFAULT_ORACLE_CHUNK_SIZE)
        if oracle_chunk_size < 1 or oracle_chunk_size > ORACLE_IN_LIMIT:
            raise ValueError(f'FREEZE_ORACLE_CHUNK_SIZE must be between 1 and {ORACLE_IN_LIMIT}')

        batch_size = config.FREEZE_BATCH_SIZE
        batches = min(math.ceil(total / batch_size), config.FREEZE_BATCHES)
        max_num = min(total, config.FREEZE_BATCHES * config.FREEZE_BATCH_SIZE)

        flow_run_id = get_run_context().flow_run.id
        colin_tracking_service = ColinTrackingService(
            config.DATA_LOAD_ENV,
            colin_extract_engine,
            FLOW_NAME,
            'colin_tracking'
        )
        reserved_corps = reserve_unprocessed_corps(config, colin_tracking_service, flow_run_id, max_num)
        print(f'👷 Reserved {reserved_corps} corps for processing')
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
                print('No more corps available to claim')
                break

            chunks = chunk_list(corp_nums, oracle_chunk_size)
            print(
                f'👷 Start processing {len(corp_nums)} corps in '
                f'{len(chunks)} Oracle chunks of <={oracle_chunk_size}: '
                f'{", ".join(corp_nums[:5])}...'
            )

            futures = []
            for chunk in chunks:
                futures.append(
                    update_colin_oracle_chunk.submit(
                        config,
                        colin_oracle_engine,
                        chunk,
                    )
                )

            complete = 0
            failed = 0
            for f in futures:
                results = f.result()
                chunk_complete, chunk_failed = record_oracle_results(
                    colin_tracking_service,
                    flow_run_id,
                    results,
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
