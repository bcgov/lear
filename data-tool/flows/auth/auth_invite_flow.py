from prefect import flow
from prefect.context import get_run_context
from prefect.states import Failed
from prefect.task_runners import ConcurrentTaskRunner

from common.extract_tracking_service import ProcessingStatuses
from common.init_utils import colin_extract_init, get_config

from .auth_flow_utils import auth_invite_identity
from .auth_models import AuthCreatePlan
from .auth_orchestration import (
    AUTH_INVITE_ACTION_FIELDS,
    AuthReservationOptions,
    AuthSubmittedTask,
    build_auth_repeatable_campaign,
    build_auth_tracking_services,
    calculate_max_corps,
    claim_auth_batch,
    count_auth_reservable,
    describe_auth_effective_selection,
    fetch_auth_profiles,
    finalize_auth_task_results,
    get_auth_max_workers,
    get_batch_token_or_mark_failed,
    insert_component_operations_or_failed,
    log_auth_config_preflight,
    parse_auth_selection_mode,
    planned_failure_actions,
    reserve_auth_candidates,
    validate_auth_throughput,
)
from .auth_tasks import perform_auth_create_for_corp


@flow(
    name='Auth-Invite-Flow',
    log_prints=True,
    persist_result=False,
    task_runner=ConcurrentTaskRunner(max_workers=get_auth_max_workers())
)
def auth_invite_flow():
    """
    Send unaffiliated invite for an entity.

    This flow is invite-only. Run auth_contact_flow first if contact repair is needed.
    (Affiliations are mutually exclusive with invites; this flow does invites only.)

    Repeatable by Auth identity; each real run creates a new auth_processing attempt row.
    """
    config = get_config()
    selection_mode = parse_auth_selection_mode(config)

    plan = AuthCreatePlan(
        create_entity=False,
        upsert_contact=False,
        create_affiliations=False,
        send_unaffiliated_invite=True,
        fail_if_missing_email=bool(getattr(config, 'AUTH_FAIL_IF_MISSING_EMAIL', False)),
        dry_run=bool(getattr(config, 'AUTH_DRY_RUN', False)),
    )

    log_auth_config_preflight(
        config,
        selection_mode,
        flow_label='invite',
        dry_run=plan.dry_run,
        campaign_scope_applies=True,
    )

    flow_run_id = get_run_context().flow_run.id
    campaign = build_auth_repeatable_campaign(
        config,
        selection_mode,
        dry_run=plan.dry_run,
        flow_label='invite',
    )
    identity = auth_invite_identity(flow_run_id, dry_run=plan.dry_run, campaign=campaign)
    print(f'👷 {describe_auth_effective_selection(config, selection_mode, dry_run=plan.dry_run, campaign=campaign)}')
    colin_engine = colin_extract_init(config)

    total_reservable = count_auth_reservable(
        colin_engine=colin_engine,
        config=config,
        selection_mode=selection_mode,
        identity=identity,
    )
    if total_reservable <= 0:
        print('No reservable corps found for this run.')
        return

    validate_auth_throughput(config)
    batch_size = config.AUTH_BATCH_SIZE
    max_corps = calculate_max_corps(config, total_reservable)

    tracking, auth_tracking, log_component_operations = build_auth_tracking_services(config, colin_engine, identity)
    reservation = reserve_auth_candidates(
        config=config,
        tracking=tracking,
        identity=identity,
        flow_run_id=flow_run_id,
        selection_mode=selection_mode,
        batch_size=batch_size,
        max_corps=max_corps,
        options=AuthReservationOptions(include_contact_email=True),
    )

    if reservation.reserved <= 0:
        print('No corps reserved (cohort may be exhausted or already reserved).')
        return

    print(f'👷 Auth invite plan: {plan}')
    print(
        f'👷 Reservable={total_reservable}, Reserved={reservation.reserved}, '
        f'Batches={reservation.batches}, BatchSize={batch_size}'
    )

    cnt = 0
    total_failed = 0
    total_completed = 0

    token_failure_actions = planned_failure_actions(
        entity=False,
        contact=False,
        affiliation=False,
        invite=True,
        action_detail='token_error',
    )
    profile_failure_actions = planned_failure_actions(
        entity=False,
        contact=False,
        affiliation=False,
        invite=True,
        action_detail='profile_missing',
    )
    task_failure_actions = planned_failure_actions(
        entity=False,
        contact=False,
        affiliation=False,
        invite=True,
        action_detail='task_result_error',
    )

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
        profiles = fetch_auth_profiles(colin_engine, corp_nums, getattr(config, 'CORP_NAME_SUFFIX', '') or '')

        token, failed_state = get_batch_token_or_mark_failed(
            config=config,
            tracking=tracking,
            flow_run_id=flow_run_id,
            corp_nums=corp_nums,
            failure_actions=token_failure_actions,
        )
        if failed_state:
            return failed_state

        submitted: list[AuthSubmittedTask] = []
        for corp_num in corp_nums:
            profile = profiles.get(corp_num)
            if not profile:
                total_failed += 1
                tracking.update_corp_status(
                    flow_run_id,
                    corp_num,
                    ProcessingStatuses.FAILED,
                    error='Missing business profile for corp in COLIN extract',
                    **profile_failure_actions,
                )
                continue

            future = perform_auth_create_for_corp.submit(
                config,
                corp_num,
                profile,
                [],
                plan,
                token,
                auth_processing_id=claimed_by_corp[corp_num]['id'],
                identity=identity,
                flow_run_id=flow_run_id,
                log_component_operations=log_component_operations,
            )
            submitted.append(AuthSubmittedTask(future, corp_num, task_failure_actions))

        finalization = finalize_auth_task_results(
            tracking=tracking,
            flow_run_id=flow_run_id,
            submitted=submitted,
            status_action_fields=AUTH_INVITE_ACTION_FIELDS,
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

    if total_failed > 0:
        return Failed(message=f'{total_failed} corps failed in {identity.flow_name}.')

    print(f'🌰 {identity.flow_name} complete. Completed={total_completed}, Failed={total_failed}')


if __name__ == '__main__':
    auth_invite_flow()
