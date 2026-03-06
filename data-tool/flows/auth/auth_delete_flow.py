import math
import os
from typing import List

from prefect import flow
from prefect.context import get_run_context
from prefect.futures import wait
from prefect.states import Failed
from prefect.task_runners import ConcurrentTaskRunner
from sqlalchemy import text

from common.extract_tracking_service import ExtractTrackingService, ProcessingStatuses
from common.init_utils import colin_extract_init, get_config

from .auth_models import AuthDeletePlan, AuthSelectionMode
from .auth_queries import (
    get_auth_reservable_corps_query,
    get_auth_reservable_count_query,
)
from .auth_tasks import get_auth_token, parse_accounts_csv, perform_auth_delete_for_corp

FLOW_NAME = 'auth-delete-flow'


def _get_max_workers() -> int:
    try:
        v = int(os.getenv('AUTH_MAX_WORKERS', '50'))
        return v if v > 0 else 50
    except Exception:
        return 50


def _parse_selection_mode(config) -> AuthSelectionMode:
    raw = (getattr(config, 'AUTH_SELECTION_MODE', 'MIGRATION_FILTER') or 'MIGRATION_FILTER').strip().upper()
    try:
        return AuthSelectionMode(raw)
    except Exception as e:
        raise ValueError(f'Unknown AUTH_SELECTION_MODE: {raw}') from e


@flow(
    name='Auth-Delete-Flow',
    log_prints=True,
    persist_result=False,
    task_runner=ConcurrentTaskRunner(max_workers=_get_max_workers())
)
def auth_delete_flow():
    """
    Delete affiliations (optional) and delete entity (optional).

    SAFETY: If AUTH_REQUIRE_CONFIRMATION is True, AUTH_CONFIRMATION_TOKEN must be set (non-empty),
    or the flow will fail fast before reserving/claiming.

    Selection excludes any corp already tracked in auth_processing for (corp_num, FLOW_NAME, environment).
    """
    config = get_config()
    colin_engine = colin_extract_init(config)

    # Safety gate
    if bool(getattr(config, 'AUTH_REQUIRE_CONFIRMATION', False)):
        if not (getattr(config, 'AUTH_CONFIRMATION_TOKEN', '') or '').strip():
            raise ValueError('AUTH_REQUIRE_CONFIRMATION is True but AUTH_CONFIRMATION_TOKEN is not set.')
        print('🛑 Delete confirmation token is present (value not displayed). Proceeding.')

    selection_mode = _parse_selection_mode(config)

    plan = AuthDeletePlan(
        delete_affiliations=bool(getattr(config, 'AUTH_DELETE_AFFILIATIONS', False)),
        delete_entity=bool(getattr(config, 'AUTH_DELETE_ENTITY', False)),
        delete_invites=bool(getattr(config, 'AUTH_DELETE_INVITES', False)),
        dry_run=bool(getattr(config, 'AUTH_DRY_RUN', False)),
    )

    # Count reservable
    count_sql = get_auth_reservable_count_query(
        flow_name=FLOW_NAME,
        config=config,
        selection_mode=selection_mode
    )
    with colin_engine.connect() as conn:
        total_reservable = int(conn.execute(text(count_sql)).scalar() or 0)

    if total_reservable <= 0:
        print('No reservable corps found for this run.')
        return

    # Throughput config
    if getattr(config, 'AUTH_BATCHES', 0) <= 0:
        raise ValueError('AUTH_BATCHES must be explicitly set to a positive integer')
    if getattr(config, 'AUTH_BATCH_SIZE', 0) <= 0:
        raise ValueError('AUTH_BATCH_SIZE must be explicitly set to a positive integer')

    batch_size = config.AUTH_BATCH_SIZE
    max_corps = min(total_reservable, config.AUTH_BATCHES * config.AUTH_BATCH_SIZE)

    flow_run_id = get_run_context().flow_run.id

    tracking = ExtractTrackingService(
        config.DATA_LOAD_ENV,
        colin_engine,
        FLOW_NAME,
        table_name='auth_processing',
        statement_timeout_ms=getattr(config, 'RESERVE_STATEMENT_TIMEOUT_MS', None)
    )

    include_account_ids = bool(plan.delete_affiliations)

    extra_insert_cols: List[str] = []
    if include_account_ids:
        extra_insert_cols.append('account_ids')

    base_query = get_auth_reservable_corps_query(
        flow_name=FLOW_NAME,
        config=config,
        batch_size=max_corps,
        selection_mode=selection_mode,
        include_account_ids=include_account_ids,
        include_contact_email=False
    )

    fallback_accounts = config.AFFILIATE_ENTITY_ACCOUNT_IDS_CSV if include_account_ids else None
    reserved = tracking.reserve_for_flow(
        base_query=base_query,
        flow_run_id=flow_run_id,
        extra_insert_cols=extra_insert_cols or None,
        fallback_account_ids=fallback_accounts
    )

    if reserved <= 0:
        print('No corps reserved (cohort may be exhausted or already reserved).')
        return

    batches = min(math.ceil(reserved / batch_size), config.AUTH_BATCHES)

    print(f'👷 Auth delete plan: {plan}')
    print(f'👷 Reservable={total_reservable}, Reserved={reserved}, Batches={batches}, BatchSize={batch_size}')
    print(f'👷 SelectionMode={selection_mode.value}, DryRun={plan.dry_run}')

    cnt = 0
    total_failed = 0
    total_completed = 0

    while cnt < batches:
        claimed = tracking.claim_batch(
            flow_run_id,
            batch_size,
            extra_return_cols=extra_insert_cols or None,
            as_dict=True
        )
        if not claimed:
            print('No more corps available to claim')
            break

        corp_nums = [r['corp_num'] for r in claimed]
        corp_accounts = {r['corp_num']: (r.get('account_ids') or None) for r in claimed} if include_account_ids else {}

        try:
            token = get_auth_token(config)
        except Exception as e:
            err = f'Failed to obtain auth token: {repr(e)}'
            print(f'❌ {err}')
            for corp_num in corp_nums:
                tracking.update_corp_status(
                    flow_run_id,
                    corp_num,
                    ProcessingStatuses.FAILED,
                    error=err,
                    entity_action='FAILED' if plan.delete_entity else 'NOT_RUN',
                    contact_action='NOT_RUN',
                    affiliation_action='FAILED' if plan.delete_affiliations else 'NOT_RUN',
                    invite_action='FAILED' if plan.delete_invites else 'NOT_RUN',
                    action_detail='token_error'
                )
            return Failed(message=err)

        futures = []
        for corp_num in corp_nums:
            accounts = parse_accounts_csv(corp_accounts.get(corp_num)) if include_account_ids else []
            futures.append(
                perform_auth_delete_for_corp.submit(
                    config,
                    corp_num,
                    accounts,
                    plan,
                    token
                )
            )

        wait(futures)

        for f in futures:
            res = f.result()
            actions = [
                res.get('entity_action'),
                res.get('contact_action'),
                res.get('affiliation_action'),
                res.get('invite_action'),
            ]
            failed = any(a == 'FAILED' for a in actions if a)
            status = ProcessingStatuses.FAILED if failed else ProcessingStatuses.COMPLETED

            tracking.update_corp_status(
                flow_run_id,
                res['corp_num'],
                status,
                error=res.get('error'),
                entity_action=res.get('entity_action'),
                contact_action=res.get('contact_action'),
                affiliation_action=res.get('affiliation_action'),
                invite_action=res.get('invite_action'),
                action_detail=res.get('action_detail')
            )

            if status == ProcessingStatuses.FAILED:
                total_failed += 1
            else:
                total_completed += 1

        cnt += 1
        print(f'🌟 Complete round {cnt}/{batches}. Completed={total_completed}, Failed={total_failed}')

    if total_failed > 0:
        return Failed(message=f'{total_failed} corps failed in {FLOW_NAME}.')

    print(f'🌰 {FLOW_NAME} complete. Completed={total_completed}, Failed={total_failed}')


if __name__ == '__main__':
    auth_delete_flow()
