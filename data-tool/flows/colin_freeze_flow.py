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
    mig_group_ids  = config.MIG_GROUP_IDS
    mig_batch_ids  = config.MIG_BATCH_IDS

    cte_clause, where_clause = get_onboarding_group_subquery()

    if use_mig_filter:
        mig_select = "b.id AS mig_batch_id,"
        mig_join   = """
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
        mig_join   = ""
        mig_extra  = ""

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


@task(cache_policy=NO_CACHE)
def update_colin_oracle(config, colin_oracle_engine: Engine, corp_num: str):
    with colin_oracle_engine.connect() as conn:
        transaction = conn.begin()
        try:
            res1, res2 = None, None
            colin_corp_num = convert_to_colin_format(corp_num)
            if config.FREEZE_COLIN_CORPS:
                res1 = conn.execute(
                    text(colin_freeze_query),
                    {'corp_num': colin_corp_num}
                )
            if config.FREEZE_ADD_EARLY_ADOPTER:
                res2 = conn.execute(
                    text(colin_add_early_adopters_query),
                    {'corp_num': colin_corp_num}
                )
            frozen = res1.rowcount > 0 if res1 else False
            in_early_adopter = res2.rowcount > 0 if res2 else False
            transaction.commit()
            return corp_num, frozen, in_early_adopter, None
        except Exception as e:
            transaction.rollback()
            print(f'❌ Error updating {corp_num} in colin: {repr(e)}')
            return corp_num, False, False, e


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
        batch_size = config.FREEZE_BATCH_SIZE
        batches = min(math.ceil(total/batch_size), config.FREEZE_BATCHES)
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
                print("No more corps available to claim")
                break

            print(f'👷 Start processing {len(corp_nums)} corps: {", ".join(corp_nums[:5])}...')

            futures = []
            for corp_num in corp_nums:
                futures.append(
                    update_colin_oracle.submit(
                        config, colin_oracle_engine, corp_num)
                )
            complete = 0
            failed = 0
            for f in futures:
                corp_num, frozen, in_early_adopter, error = f.result()
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
