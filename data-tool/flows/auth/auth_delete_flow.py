from prefect import flow
from prefect.context import get_run_context
from prefect.futures import wait
from prefect.states import Failed
from prefect.task_runners import ConcurrentTaskRunner

from common.extract_tracking_service import ProcessingStatuses
from common.init_utils import colin_extract_init, get_config

from .auth_flow_utils import AUTH_DELETE_FLOW_NAME, auth_delete_identity
from .auth_models import AuthDeletePlan, AuthDeleteTrackingCleanupMode, AuthOperationScope
from .auth_orchestration import (
    AUTH_ALL_ACTION_FIELDS,
    AuthReservationOptions,
    AuthSubmittedTask,
    build_auth_repeatable_campaign,
    build_auth_tracking_services,
    calculate_max_corps,
    claim_auth_batch,
    count_auth_reservable,
    describe_auth_effective_selection,
    finalize_auth_task_results,
    format_auth_delete_tracking_cleanup_summary,
    get_auth_max_workers,
    get_batch_token_or_mark_failed,
    has_failed_action,
    insert_component_operations_or_failed,
    log_auth_config_preflight,
    parse_auth_delete_tracking_cleanup_mode,
    parse_auth_selection_mode,
    planned_failure_actions,
    reserve_auth_candidates,
    task_result_error,
    update_auth_processing_from_task_result,
    validate_auth_delete_flow_plan,
    validate_auth_throughput,
)
from .auth_queries import get_auth_selected_corp_nums_query
from .auth_tasks import parse_accounts_csv, perform_auth_delete_for_corp
from .auth_tracking import AuthComponentOperationRecord, AuthTrackingService


@flow(
    name='Auth-Delete-Flow',
    log_prints=True,
    persist_result=False,
    task_runner=ConcurrentTaskRunner(max_workers=get_auth_max_workers())
)
def auth_delete_flow():
    """
    Delete Auth components (repeatable) or fully reset Auth entities (reset semantics).

    Failed or interrupted non-dry-run RESET/FULL_ENTITY rows intentionally block future reset
    selection until manually deleted.
    """
    config = get_config()

    cleanup_mode = parse_auth_delete_tracking_cleanup_mode(config)
    if cleanup_mode != AuthDeleteTrackingCleanupMode.OFF:
        selection_mode = parse_auth_selection_mode(config)
        log_auth_config_preflight(
            config,
            selection_mode,
            flow_label='delete cleanup',
            dry_run=False,
            campaign_scope_applies=False,
        )
        if bool(getattr(config, 'AUTH_DELETE_AFFILIATIONS', False)) or bool(getattr(config, 'AUTH_DELETE_ENTITY', False)):
            print('👷 AUTH_DELETE_TRACKING_CLEANUP_MODE is set; ignoring Auth API delete flags.')
        selected_corp_nums_sql = get_auth_selected_corp_nums_query(config, selection_mode)
        colin_engine = colin_extract_init(config)
        auth_tracking = AuthTrackingService.from_config(config, colin_engine)
        summary = auth_tracking.preview_delete_tracking_cleanup(
            selected_corp_nums_sql,
            flow_name=AUTH_DELETE_FLOW_NAME,
        )
        for line in format_auth_delete_tracking_cleanup_summary(summary):
            print(f'👷 {line}')
        if cleanup_mode == AuthDeleteTrackingCleanupMode.PREVIEW:
            print('👷 Auth delete tracking cleanup PREVIEW complete; no rows deleted.')
            return

        deleted = auth_tracking.execute_delete_tracking_cleanup(
            selected_corp_nums_sql,
            flow_name=AUTH_DELETE_FLOW_NAME,
        )
        print(f'👷 Auth delete tracking cleanup EXECUTE deleted auth_processing rows: {deleted}')
        if deleted != summary.total_auth_processing_rows:
            print(
                '⚠️ Auth delete tracking cleanup deleted rowcount differs from preview: '
                f'preview={summary.total_auth_processing_rows}, deleted={deleted}'
            )
        return

    plan = AuthDeletePlan(
        delete_affiliations=bool(getattr(config, 'AUTH_DELETE_AFFILIATIONS', False)),
        delete_entity=bool(getattr(config, 'AUTH_DELETE_ENTITY', False)),
        dry_run=bool(getattr(config, 'AUTH_DRY_RUN', False)),
    )
    validate_auth_delete_flow_plan(plan)

    selection_mode = parse_auth_selection_mode(config)
    log_auth_config_preflight(
        config,
        selection_mode,
        flow_label='delete',
        dry_run=plan.dry_run,
        campaign_scope_applies=bool(plan.delete_entity or plan.delete_affiliations),
    )

    flow_run_id = get_run_context().flow_run.id
    full_reset_sweep = plan.delete_entity and not plan.dry_run
    campaign = None
    if full_reset_sweep:
        print(
            '👷 Auth delete mode: full reset sweep '
            '(AUTH_DELETE_ENTITY=True, AUTH_DRY_RUN=False); '
            'AUTH_REPEATABLE_CYCLE_KEY is required because sweep tracking uses a campaign identity.'
        )
        campaign = build_auth_repeatable_campaign(
            config,
            selection_mode,
            dry_run=plan.dry_run,
            missing_cycle_key_message=(
                'AUTH_REPEATABLE_CYCLE_KEY is required for non-dry-run auth delete full reset '
                '(AUTH_DELETE_ENTITY=True, AUTH_DRY_RUN=False) because full reset uses sweep tracking'
            ),
            flow_label='delete full reset',
        )
    elif plan.delete_affiliations and not plan.delete_entity:
        print('👷 Auth delete mode: affiliation-only repeatable delete')
        campaign = build_auth_repeatable_campaign(
            config,
            selection_mode,
            dry_run=plan.dry_run,
            flow_label='delete',
        )
    elif plan.delete_entity:
        print('👷 Auth delete mode: dry-run full reset (no sweep tracking campaign required)')
    identity = auth_delete_identity(plan, flow_run_id, campaign=campaign)
    print(f'👷 {describe_auth_effective_selection(config, selection_mode, dry_run=plan.dry_run, campaign=campaign)}')
    colin_engine = colin_extract_init(config)

    tracking, auth_tracking, log_component_operations = build_auth_tracking_services(config, colin_engine, identity)

    # Count reservable with reset blockers left in place until manual cleanup.
    total_reservable = count_auth_reservable(
        colin_engine=colin_engine,
        config=config,
        selection_mode=selection_mode,
        identity=identity,
    )
    if total_reservable <= 0:
        print('No reservable corps found for this run.')
        return

    # Throughput config is validated before reservation.
    validate_auth_throughput(config)
    batch_size = config.AUTH_BATCH_SIZE
    max_corps = calculate_max_corps(config, total_reservable)
    include_account_ids = bool(plan.delete_affiliations)

    reservation = reserve_auth_candidates(
        config=config,
        tracking=tracking,
        identity=identity,
        flow_run_id=flow_run_id,
        selection_mode=selection_mode,
        batch_size=batch_size,
        max_corps=max_corps,
        options=AuthReservationOptions(include_account_ids=include_account_ids),
    )

    if reservation.reserved <= 0:
        print('No corps reserved (cohort may be exhausted or already reserved).')
        return

    print(f'👷 Auth delete plan: {plan}')
    print(
        f'👷 Reservable={total_reservable}, Reserved={reservation.reserved}, '
        f'Batches={reservation.batches}, BatchSize={batch_size}'
    )
    print(
        f'👷 TrackingFlow={identity.flow_name}, '
        f'Identity={identity.operation.value}/{identity.operation_scope.value}'
    )

    cnt = 0
    total_failed = 0
    total_completed = 0

    token_failure_actions = planned_failure_actions(
        entity=plan.delete_entity,
        contact=False,
        affiliation=plan.delete_affiliations,
        invite=False,
        action_detail='token_error',
    )
    task_failure_actions = planned_failure_actions(
        entity=plan.delete_entity,
        contact=False,
        affiliation=plan.delete_affiliations,
        invite=False,
        action_detail='task_result_error',
    )
    is_affiliation_only_delete = plan.delete_affiliations and not plan.delete_entity
    missing_accounts_actions = {
        'entity_action': 'NOT_RUN',
        'contact_action': 'NOT_RUN',
        'affiliation_action': 'FAILED',
        'invite_action': 'NOT_RUN',
        'action_detail': 'delete_affiliations_missing_accounts',
    }
    missing_accounts_error = 'Delete affiliations requires account coverage; no account_ids resolved for corp.'
    is_non_dry_run_full_reset = plan.delete_entity and not plan.dry_run

    while cnt < reservation.batches:
        claimed = claim_auth_batch(
            tracking=tracking,
            flow_run_id=flow_run_id,
            batch_size=batch_size,
            extra_insert_cols=reservation.extra_insert_cols,
        )
        if not claimed:
            print('No more corps available to claim')
            break

        corp_nums = [r['corp_num'] for r in claimed]
        claimed_by_corp = {r['corp_num']: r for r in claimed}
        corp_accounts = {r['corp_num']: (r.get('account_ids') or None) for r in claimed} if include_account_ids else {}
        parsed_accounts_by_corp = {
            corp_num: parse_accounts_csv(corp_accounts.get(corp_num)) if include_account_ids else []
            for corp_num in corp_nums
        }

        processable_corp_nums = corp_nums
        if is_affiliation_only_delete:
            processable_corp_nums = []
            for corp_num in corp_nums:
                if parsed_accounts_by_corp.get(corp_num):
                    processable_corp_nums.append(corp_num)
                    continue
                tracking.update_corp_status(
                    flow_run_id,
                    corp_num,
                    ProcessingStatuses.FAILED,
                    error=missing_accounts_error,
                    **missing_accounts_actions,
                )
                total_failed += 1

        if not processable_corp_nums:
            cnt += 1
            print(
                f'🌟 Complete round {cnt}/{reservation.batches}. '
                f'Completed={total_completed}, Failed={total_failed}'
            )
            continue

        token, failed_state = get_batch_token_or_mark_failed(
            config=config,
            tracking=tracking,
            flow_run_id=flow_run_id,
            corp_nums=processable_corp_nums,
            failure_actions=token_failure_actions,
        )
        if failed_state:
            return failed_state

        submitted: list[AuthSubmittedTask] = []
        for corp_num in processable_corp_nums:
            accounts = parsed_accounts_by_corp.get(corp_num, [])
            future = perform_auth_delete_for_corp.submit(
                config,
                corp_num,
                accounts,
                plan,
                token,
                auth_processing_id=claimed_by_corp[corp_num]['id'],
                identity=identity,
                flow_run_id=flow_run_id,
                log_component_operations=log_component_operations,
            )
            submitted.append(AuthSubmittedTask(future, corp_num, task_failure_actions))

        if not is_non_dry_run_full_reset:
            finalization = finalize_auth_task_results(
                tracking=tracking,
                flow_run_id=flow_run_id,
                submitted=submitted,
                status_action_fields=AUTH_ALL_ACTION_FIELDS,
            )
            total_failed += finalization.failed
            total_completed += finalization.completed
            insert_failed_state = insert_component_operations_or_failed(
                auth_tracking,
                finalization.component_operations,
            )
            if insert_failed_state:
                return insert_failed_state

            cnt += 1
            print(f'🌟 Complete round {cnt}/{reservation.batches}. Completed={total_completed}, Failed={total_failed}')
            continue

        if submitted:
            wait([item.future for item in submitted])

        component_operations = []
        cleanup_errors = []
        for item in submitted:
            try:
                res = item.future.result()
            except Exception as e:
                err = task_result_error(e)
                tracking.update_corp_status(
                    flow_run_id,
                    item.corp_num,
                    ProcessingStatuses.FAILED,
                    error=err,
                    **item.failure_actions,
                )
                total_failed += 1
                continue

            failed = has_failed_action(res, AUTH_ALL_ACTION_FIELDS)

            if not failed:
                try:
                    preserve_auth_processing_id = (
                        claimed_by_corp[res['corp_num']]['id']
                        if full_reset_sweep
                        else None
                    )
                    auth_tracking.cleanup_full_reset_tracking(
                        res['corp_num'],
                        preserve_auth_processing_id=preserve_auth_processing_id,
                    )
                except Exception as e:
                    err = f'Full reset tracking cleanup failed: {repr(e)}'
                    detail = 'reset_cleanup_error'
                    if res.get('action_detail'):
                        detail = f"{res.get('action_detail')}; {detail}"
                    print(f'❌ {err}')
                    tracking.update_corp_status(
                        flow_run_id,
                        res['corp_num'],
                        ProcessingStatuses.FAILED,
                        error=err,
                        entity_action=res.get('entity_action'),
                        contact_action=res.get('contact_action'),
                        affiliation_action=res.get('affiliation_action'),
                        invite_action=res.get('invite_action'),
                        action_detail=detail,
                    )
                    component_operations.extend(res.get('component_operations') or [])
                    if log_component_operations:
                        component_operations.append(
                            AuthComponentOperationRecord(
                                auth_processing_id=claimed_by_corp[res['corp_num']]['id'],
                                corp_num=res['corp_num'],
                                flow_name=identity.flow_name,
                                environment=config.DATA_LOAD_ENV,
                                flow_run_id=flow_run_id,
                                operation=identity.operation,
                                operation_scope=identity.operation_scope,
                                component=AuthOperationScope.FULL_ENTITY,
                                target_type='tracking',
                                target_value=res['corp_num'],
                                action='CLEANUP_FULL_RESET_TRACKING',
                                error=err,
                                detail='result:FAILED; reset_cleanup_error',
                                dry_run=plan.dry_run,
                            )
                        )
                    total_failed += 1
                    cleanup_errors.append(err)
                    continue

                if full_reset_sweep:
                    update_auth_processing_from_task_result(
                        tracking=tracking,
                        flow_run_id=flow_run_id,
                        result=res,
                        status=ProcessingStatuses.COMPLETED,
                    )
                    component_operations.extend(res.get('component_operations') or [])

                total_completed += 1
                continue

            update_auth_processing_from_task_result(
                tracking=tracking,
                flow_run_id=flow_run_id,
                result=res,
                status=ProcessingStatuses.FAILED,
            )
            component_operations.extend(res.get('component_operations') or [])
            total_failed += 1

        insert_failed_state = insert_component_operations_or_failed(auth_tracking, component_operations)
        if insert_failed_state:
            return insert_failed_state

        if cleanup_errors:
            return Failed(message='; '.join(cleanup_errors[:3]))

        cnt += 1
        print(f'🌟 Complete round {cnt}/{reservation.batches}. Completed={total_completed}, Failed={total_failed}')

    if total_failed > 0:
        return Failed(message=f'{total_failed} corps failed in {identity.flow_name}.')

    print(f'🌰 {identity.flow_name} complete. Completed={total_completed}, Failed={total_failed}')


if __name__ == '__main__':
    auth_delete_flow()
