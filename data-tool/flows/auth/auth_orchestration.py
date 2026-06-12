from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from typing import Any, Optional

from prefect.futures import wait
from prefect.states import Failed
from sqlalchemy import text

from common.extract_tracking_service import ExtractTrackingService, ProcessingStatuses
from common.query_utils import convert_result_set_to_dict

from .auth_flow_utils import AUTH_PROCESSING_IDENTITY_CONFLICT_COLUMNS, build_auth_attempt_key_from_context
from .auth_models import (
    AuthCreatePlan,
    AuthDeletePlan,
    AuthDeleteTrackingCleanupMode,
    AuthProcessingIdentity,
    AuthRepeatableCampaign,
    AuthSelectionMode,
)
from .auth_queries import (
    get_auth_business_profiles_query,
    get_auth_query_params,
    get_auth_reservable_corps_query,
    get_auth_reservable_count_query,
)
from .auth_selection import (
    auth_migration_filter_ids,
    corp_nums_scope_hash,
    corp_nums_subset_scope,
    parse_auth_corp_nums_csv,
    parse_positive_int_csv,
    positive_int_csv_for_scope,
)
from .auth_tasks import get_auth_token
from .auth_tracking import AuthComponentOperationRecord, AuthTrackingService


AUTH_ALL_ACTION_FIELDS = (
    'entity_action',
    'contact_action',
    'affiliation_action',
    'invite_action',
)
AUTH_CONTACT_ACTION_FIELDS = ('contact_action',)
AUTH_INVITE_ACTION_FIELDS = ('invite_action',)


@dataclass(frozen=True)
class AuthReservationOptions:
    include_account_ids: bool = False
    include_contact_email: bool = False


@dataclass(frozen=True)
class AuthReservationResult:
    reserved: int
    batches: int
    extra_insert_cols: list[str]


@dataclass(frozen=True)
class AuthSubmittedTask:
    future: Any
    corp_num: str
    failure_actions: dict[str, str]


@dataclass(frozen=True)
class AuthBatchFinalizationResult:
    completed: int
    failed: int
    component_operations: list[AuthComponentOperationRecord]


def get_auth_max_workers() -> int:
    try:
        v = int(os.getenv('AUTH_MAX_WORKERS', '50'))
        return v if v > 0 else 50
    except Exception:
        return 50


def parse_auth_selection_mode(config) -> AuthSelectionMode:
    raw = (getattr(config, 'AUTH_SELECTION_MODE', 'MIGRATION_FILTER') or 'MIGRATION_FILTER').strip().upper()
    try:
        return AuthSelectionMode(raw)
    except Exception as e:
        raise ValueError(f'Unknown AUTH_SELECTION_MODE: {raw}') from e


def parse_auth_delete_tracking_cleanup_mode(config) -> AuthDeleteTrackingCleanupMode:
    """Return normalized auth delete tracking cleanup mode."""
    raw = (getattr(config, 'AUTH_DELETE_TRACKING_CLEANUP_MODE', 'OFF') or 'OFF').strip().upper()
    try:
        return AuthDeleteTrackingCleanupMode(raw)
    except Exception as e:
        allowed = ', '.join(mode.value for mode in AuthDeleteTrackingCleanupMode)
        raise ValueError(f'Unknown AUTH_DELETE_TRACKING_CLEANUP_MODE: {raw}; expected one of {allowed}') from e


_CYCLE_KEY_RE = re.compile(r'^[A-Za-z0-9_.:-]+$')
_CAMPAIGN_SCOPE_RE = re.compile(r'^[A-Za-z0-9_.:/=-]+$')
_MAX_CYCLE_KEY_LEN = 80
_MAX_EXPLICIT_SCOPE_LEN = 240
_MAX_OPERATION_TARGET_LEN = 500


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _preview_text(value: str, max_len: int) -> str:
    if max_len <= 0:
        return ''
    if len(value) <= max_len:
        return value
    if max_len == 1:
        return value[:1]
    return f'{value[:max_len - 1]}~'


def normalize_auth_repeatable_cycle_key(config, *, missing_message: str | None = None) -> str:
    """Return normalized AUTH_REPEATABLE_CYCLE_KEY or raise for real auth flows."""
    cycle_key = str(getattr(config, 'AUTH_REPEATABLE_CYCLE_KEY', '') or '').strip()
    if not cycle_key:
        raise ValueError(missing_message or 'AUTH_REPEATABLE_CYCLE_KEY is required for non-dry-run repeatable auth flows')
    if len(cycle_key) > _MAX_CYCLE_KEY_LEN:
        raise ValueError(f'AUTH_REPEATABLE_CYCLE_KEY must be {_MAX_CYCLE_KEY_LEN} characters or fewer')
    if not _CYCLE_KEY_RE.fullmatch(cycle_key):
        raise ValueError('AUTH_REPEATABLE_CYCLE_KEY may contain only letters, digits, underscore, dash, dot, and colon')
    return cycle_key


def validate_auth_cycle_key_for_flow(
    config,
    *,
    flow_label: str,
    dry_run: bool,
    missing_message: str | None = None,
    log_context: str | None = None,
) -> str | None:
    """Validate/log the normalized auth cycle key for non-dry-run flow entrypoints."""
    if dry_run:
        return None

    label = str(flow_label or '').strip() or 'flow'
    cycle_key = normalize_auth_repeatable_cycle_key(
        config,
        missing_message=missing_message or f'AUTH_REPEATABLE_CYCLE_KEY is required for non-dry-run auth {label} runs',
    )
    context = f' ({log_context})' if log_context else ''
    print(f'👷 Auth {label} cycle key: {cycle_key}{context}')
    return cycle_key


def _safe_positive_int_scope(config, attr: str, name: str) -> str:
    """Return normalized CSV/ALL for preflight logs without raising on malformed config."""
    try:
        return positive_int_csv_for_scope(getattr(config, attr, None), name=name)
    except ValueError as err:
        return f'INVALID({err})'


def auth_config_preflight_lines(
    config,
    selection_mode: AuthSelectionMode,
    *,
    flow_label: str,
    dry_run: bool,
    campaign_scope_applies: bool,
) -> list[str]:
    """Return safe operator-facing Auth config context before fail-fast validation.

    This intentionally does not enforce required Auth migration IDs so operators can
    see the selected mode, subset, and campaign-scope behavior before the later
    validation raises the authoritative error.
    """
    label = str(flow_label or '').strip() or 'flow'
    selection_mode = AuthSelectionMode(selection_mode)
    lines: list[str] = []

    if selection_mode == AuthSelectionMode.MIGRATION_FILTER:
        group_scope = _safe_positive_int_scope(config, 'AUTH_MIG_GROUP_IDS', 'AUTH_MIG_GROUP_IDS')
        batch_scope = _safe_positive_int_scope(config, 'AUTH_MIG_BATCH_IDS', 'AUTH_MIG_BATCH_IDS')
        subset_scope = corp_nums_subset_scope(getattr(config, 'AUTH_CORP_NUMS', ''), all_label='ALL')
        lines.append(
            f'Auth {label} selection preflight: SelectionMode=MIGRATION_FILTER, '
            f'AuthMigGroups={group_scope}, AuthMigBatches={batch_scope}, Subset={subset_scope}'
        )
        lines.append(
            'Auth MIGRATION_FILTER note: AUTH_CORP_NUMS only narrows the migration-filter cohort '
            'and does not replace AUTH_MIG_GROUP_IDS/AUTH_MIG_BATCH_IDS; Auth flows do not fall back '
            'to global MIG_GROUP_IDS/MIG_BATCH_IDS.'
        )
    else:
        corp_nums = parse_auth_corp_nums_csv(getattr(config, 'AUTH_CORP_NUMS', ''))
        canonical_corp_nums = sorted(corp_nums)
        subset_scope = f'count={len(canonical_corp_nums)};sha256={corp_nums_scope_hash(canonical_corp_nums)}'
        lines.append(
            f'Auth {label} selection preflight: SelectionMode=MANUAL, '
            f'AuthCorpNums=count={len(corp_nums)}, Subset={subset_scope}'
        )
        lines.append(
            'Auth MANUAL note: AUTH_CORP_NUMS is the source list; blank AUTH_CORP_NUMS means no '
            'candidates; AUTH_MIG_GROUP_IDS/AUTH_MIG_BATCH_IDS are ignored.'
        )

    if not campaign_scope_applies:
        return lines

    if dry_run:
        lines.append(
            'Auth campaign preflight: dry-runs do not require AUTH_REPEATABLE_CAMPAIGN_SCOPE and use '
            'a flow-run-specific dry-run attempt identity.'
        )
        return lines

    explicit_scope = str(getattr(config, 'AUTH_REPEATABLE_CAMPAIGN_SCOPE', '') or '').strip()
    if explicit_scope:
        explicit_preview = _preview_text(explicit_scope, 80)
        if selection_mode == AuthSelectionMode.MIGRATION_FILTER:
            lines.append(
                f'Auth campaign preflight: AUTH_REPEATABLE_CAMPAIGN_SCOPE is explicit ({explicit_preview}); '
                'it overrides derived scope but does not bypass MIGRATION_FILTER Auth migration ID validation.'
            )
        else:
            lines.append(
                f'Auth campaign preflight: AUTH_REPEATABLE_CAMPAIGN_SCOPE is explicit ({explicit_preview}); '
                'it overrides the derived selection scope.'
            )
    else:
        lines.append(
            'Auth campaign preflight: blank AUTH_REPEATABLE_CAMPAIGN_SCOPE is valid; real-run scope '
            'will be derived from selection mode + Auth migration IDs + optional AUTH_CORP_NUMS subset hash.'
        )
    return lines


def log_auth_config_preflight(
    config,
    selection_mode: AuthSelectionMode,
    *,
    flow_label: str,
    dry_run: bool,
    campaign_scope_applies: bool,
) -> None:
    """Print safe Auth selection/campaign-scope context for flow entrypoints."""
    for line in auth_config_preflight_lines(
        config,
        selection_mode,
        flow_label=flow_label,
        dry_run=dry_run,
        campaign_scope_applies=campaign_scope_applies,
    ):
        print(f'👷 {line}')


def _normalize_explicit_campaign_scope(raw_scope: str) -> str:
    campaign_scope = str(raw_scope or '').strip()
    if not campaign_scope:
        return ''
    if len(campaign_scope) > _MAX_EXPLICIT_SCOPE_LEN:
        raise ValueError(f'AUTH_REPEATABLE_CAMPAIGN_SCOPE must be {_MAX_EXPLICIT_SCOPE_LEN} characters or fewer')
    if not _CAMPAIGN_SCOPE_RE.fullmatch(campaign_scope):
        raise ValueError('AUTH_REPEATABLE_CAMPAIGN_SCOPE may contain only letters, digits, underscore, dash, dot, colon, slash, and equals')
    return campaign_scope


def _normalized_int_scope(config, attr: str, name: str) -> str:
    values = parse_positive_int_csv(getattr(config, attr, None), name=name)
    return ','.join(values) if values else 'ALL'


def derive_auth_campaign_scope(config, selection_mode: AuthSelectionMode) -> str:
    """Derive campaign scope from selection config unless an explicit override is set."""
    selection_mode = AuthSelectionMode(selection_mode)
    if selection_mode == AuthSelectionMode.MIGRATION_FILTER:
        # Validation intentionally uses auth-specific IDs only; global MIG IDs are ignored.
        auth_migration_filter_ids(config, require_any=True)

    explicit_scope = _normalize_explicit_campaign_scope(
        getattr(config, 'AUTH_REPEATABLE_CAMPAIGN_SCOPE', '')
    )
    if explicit_scope:
        return explicit_scope

    if selection_mode == AuthSelectionMode.MIGRATION_FILTER:
        group_scope = _normalized_int_scope(config, 'AUTH_MIG_GROUP_IDS', 'AUTH_MIG_GROUP_IDS')
        batch_scope = _normalized_int_scope(config, 'AUTH_MIG_BATCH_IDS', 'AUTH_MIG_BATCH_IDS')
        subset_scope = corp_nums_subset_scope(getattr(config, 'AUTH_CORP_NUMS', ''), all_label='ALL')
        return f'MIGRATION_FILTER:groups={group_scope};batches={batch_scope};subset={subset_scope}'

    corp_nums = sorted(parse_auth_corp_nums_csv(getattr(config, 'AUTH_CORP_NUMS', '')))
    return f'MANUAL:count={len(corp_nums)};sha256={corp_nums_scope_hash(corp_nums)}'


def _build_repeatable_attempt_key_context(
    *,
    selection_mode: AuthSelectionMode,
    cycle_key: str,
    campaign_scope: str,
) -> str:
    """Build the readable canonical context for repeatable auth campaign identity."""
    mode = AuthSelectionMode(selection_mode).value
    return f'CYCLE:v1:{mode}:{cycle_key}:{campaign_scope}'


def _build_operation_target(cycle_key: str, campaign_scope: str) -> str:
    scope_hash = _sha256_text(campaign_scope)
    prefix = f'cycle={cycle_key};scope='
    suffix = f';scope_hash={scope_hash}'
    if len(prefix) + len(campaign_scope) + len(suffix) <= _MAX_OPERATION_TARGET_LEN:
        return f'{prefix}{campaign_scope}{suffix}'

    max_scope_len = max(0, _MAX_OPERATION_TARGET_LEN - len(prefix) - len(suffix) - 3)
    return f'{prefix}{campaign_scope[:max_scope_len]}...{suffix}'


def build_auth_repeatable_campaign(
    config,
    selection_mode: AuthSelectionMode,
    *,
    dry_run: bool = False,
    missing_cycle_key_message: str | None = None,
    flow_label: str | None = None,
) -> AuthRepeatableCampaign | None:
    """Build stable campaign identity for real repeatable flows; dry-runs do not need one."""
    if dry_run:
        return None

    if flow_label:
        cycle_key = validate_auth_cycle_key_for_flow(
            config,
            flow_label=flow_label,
            dry_run=dry_run,
            missing_message=missing_cycle_key_message,
        )
    else:
        cycle_key = normalize_auth_repeatable_cycle_key(config, missing_message=missing_cycle_key_message)
    campaign_scope = derive_auth_campaign_scope(config, selection_mode)
    attempt_key_context = _build_repeatable_attempt_key_context(
        selection_mode=selection_mode,
        cycle_key=cycle_key,
        campaign_scope=campaign_scope,
    )
    return AuthRepeatableCampaign(
        cycle_key=cycle_key,
        campaign_scope=campaign_scope,
        attempt_key_context=attempt_key_context,
        attempt_key=build_auth_attempt_key_from_context(attempt_key_context),
        operation_target=_build_operation_target(cycle_key, campaign_scope),
    )


def describe_auth_effective_selection(
    config,
    selection_mode: AuthSelectionMode,
    *,
    dry_run: bool,
    campaign: AuthRepeatableCampaign | None = None,
) -> str:
    """Return a concise operator-facing summary of effective auth targeting."""
    selection_mode = AuthSelectionMode(selection_mode)
    if selection_mode == AuthSelectionMode.MIGRATION_FILTER:
        auth_migration_filter_ids(config, require_any=True)
        group_scope = _normalized_int_scope(config, 'AUTH_MIG_GROUP_IDS', 'AUTH_MIG_GROUP_IDS')
        batch_scope = _normalized_int_scope(config, 'AUTH_MIG_BATCH_IDS', 'AUTH_MIG_BATCH_IDS')
        subset_scope = corp_nums_subset_scope(getattr(config, 'AUTH_CORP_NUMS', ''), all_label='ALL')
        target = f'SelectionMode=MIGRATION_FILTER, AuthMigGroups={group_scope}, AuthMigBatches={batch_scope}, Subset={subset_scope}'
    else:
        corp_nums = parse_auth_corp_nums_csv(getattr(config, 'AUTH_CORP_NUMS', ''))
        canonical_corp_nums = sorted(corp_nums)
        subset_scope = f'count={len(canonical_corp_nums)};sha256={corp_nums_scope_hash(canonical_corp_nums)}'
        target = f'SelectionMode=MANUAL, AuthCorpNums=count={len(corp_nums)}, Subset={subset_scope}'

    campaign_text = ''
    if campaign is not None:
        campaign_text = (
            f', CycleKey={campaign.cycle_key}, CampaignScope={campaign.campaign_scope}, '
            f'AttemptKey={campaign.attempt_key}, AttemptKeyContext={campaign.attempt_key_context}'
        )
    return f'{target}, DryRun={dry_run}{campaign_text}'


def validate_auth_create_flow_plan(plan: AuthCreatePlan) -> None:
    """Validate create-flow plan shape before one-shot CREATE/ENTITY reservation."""
    has_any_action = any((
        plan.create_entity,
        plan.upsert_contact,
        plan.create_affiliations,
        plan.send_unaffiliated_invite,
    ))
    if not has_any_action:
        raise ValueError('Invalid auth_create_flow plan: at least one create action must be enabled')
    if not plan.create_entity:
        raise ValueError(
            'Invalid auth_create_flow plan: AUTH_CREATE_ENTITY must be True; '
            'use dedicated contact, affiliation, or invite flows for component-only work'
        )
    if plan.create_affiliations and plan.send_unaffiliated_invite:
        raise ValueError('Invalid auth_create_flow plan: cannot both create affiliations and send unaffiliated invite')


def validate_auth_delete_flow_plan(plan: AuthDeletePlan) -> None:
    """Validate delete-flow plan shape before delete/reset reservation."""
    if not (plan.delete_affiliations or plan.delete_entity):
        raise ValueError('Invalid auth_delete_flow plan: set at least one of AUTH_DELETE_AFFILIATIONS or AUTH_DELETE_ENTITY')


def format_auth_delete_tracking_cleanup_summary(summary) -> list[str]:
    """Return compact operator-facing cleanup summary lines."""
    status_counts = ', '.join(
        f'{status}={count}' for status, count in sorted((summary.status_counts or {}).items())
    ) or 'none'
    corp_sample = ', '.join(summary.corp_sample or []) or 'none'
    return [
        f'Auth delete tracking cleanup summary ({summary.flow_name}/{summary.environment})',
        f'auth_processing rows: {summary.total_auth_processing_rows}',
        f'distinct corps: {summary.distinct_corp_count}; sample: {corp_sample}',
        f'processed_status counts: {status_counts}',
        f'estimated auth_component_operation cascade rows: {summary.estimated_component_operation_rows}',
    ]


def fetch_auth_profiles(colin_engine, corp_nums: list[str], suffix: str) -> dict[str, dict]:
    if not corp_nums:
        return {}
    sql = get_auth_business_profiles_query(corp_nums, suffix or '')
    with colin_engine.connect() as conn:
        rs = conn.execute(text(sql))
        rows = convert_result_set_to_dict(rs)
        return {r['identifier']: r for r in rows}


def task_result_error(e: Exception) -> str:
    return f'Task result error: {repr(e)}'[:1000]


def count_auth_reservable(
    *,
    colin_engine,
    config,
    selection_mode: AuthSelectionMode,
    identity: AuthProcessingIdentity,
) -> int:
    count_sql = get_auth_reservable_count_query(
        flow_name=identity.flow_name,
        config=config,
        selection_mode=selection_mode,
        identity=identity,
    )
    query_params = get_auth_query_params(identity)
    with colin_engine.connect() as conn:
        return int(conn.execute(text(count_sql), query_params).scalar() or 0)


def validate_auth_throughput(config) -> None:
    if getattr(config, 'AUTH_BATCHES', 0) <= 0:
        raise ValueError('AUTH_BATCHES must be explicitly set to a positive integer')
    if getattr(config, 'AUTH_BATCH_SIZE', 0) <= 0:
        raise ValueError('AUTH_BATCH_SIZE must be explicitly set to a positive integer')


def calculate_max_corps(config, total_reservable: int) -> int:
    return min(total_reservable, config.AUTH_BATCHES * config.AUTH_BATCH_SIZE)


def build_auth_tracking_services(config, colin_engine, identity: AuthProcessingIdentity):
    tracking = ExtractTrackingService(
        config.DATA_LOAD_ENV,
        colin_engine,
        identity.flow_name,
        table_name='auth_processing',
        statement_timeout_ms=getattr(config, 'RESERVE_STATEMENT_TIMEOUT_MS', None),
    )
    auth_tracking = AuthTrackingService.from_config(config, colin_engine)
    return tracking, auth_tracking, auth_tracking.component_logging_enabled


def reserve_auth_candidates(
    *,
    config,
    tracking: ExtractTrackingService,
    identity: AuthProcessingIdentity,
    flow_run_id,
    selection_mode: AuthSelectionMode,
    batch_size: int,
    max_corps: int,
    options: AuthReservationOptions,
) -> AuthReservationResult:
    extra_insert_cols: list[str] = []
    if options.include_account_ids:
        extra_insert_cols.append('account_ids')
    if options.include_contact_email:
        extra_insert_cols.append('contact_email')

    base_query = get_auth_reservable_corps_query(
        flow_name=identity.flow_name,
        config=config,
        batch_size=max_corps,
        selection_mode=selection_mode,
        include_account_ids=options.include_account_ids,
        include_contact_email=options.include_contact_email,
        identity=identity,
    )

    reserved = tracking.reserve_for_flow(
        base_query=base_query,
        flow_run_id=flow_run_id,
        extra_insert_cols=extra_insert_cols or None,
        fallback_account_ids=(
            getattr(config, 'AUTH_AFFILIATION_ACCOUNT_IDS_CSV', None)
            if options.include_account_ids else None
        ),
        base_query_params=get_auth_query_params(
            identity,
            config=config,
            include_contact_email=options.include_contact_email,
        ),
        static_insert_values=identity.as_insert_values(),
        conflict_columns=AUTH_PROCESSING_IDENTITY_CONFLICT_COLUMNS,
    )
    batches = min(math.ceil(reserved / batch_size), config.AUTH_BATCHES) if reserved > 0 else 0
    return AuthReservationResult(
        reserved=reserved,
        batches=batches,
        extra_insert_cols=extra_insert_cols,
    )


def claim_auth_batch(
    *,
    tracking: ExtractTrackingService,
    flow_run_id,
    batch_size: int,
    extra_insert_cols: list[str],
) -> list[dict]:
    return tracking.claim_batch(
        flow_run_id,
        batch_size,
        extra_return_cols=['id'] + extra_insert_cols,
        as_dict=True,
    )


def planned_failure_actions(
    *,
    entity: bool,
    contact: bool,
    affiliation: bool,
    invite: bool,
    action_detail: str,
) -> dict[str, str]:
    return {
        'entity_action': 'FAILED' if entity else 'NOT_RUN',
        'contact_action': 'FAILED' if contact else 'NOT_RUN',
        'affiliation_action': 'FAILED' if affiliation else 'NOT_RUN',
        'invite_action': 'FAILED' if invite else 'NOT_RUN',
        'action_detail': action_detail,
    }


def get_batch_token_or_mark_failed(
    *,
    config,
    tracking: ExtractTrackingService,
    flow_run_id,
    corp_nums: list[str],
    failure_actions: dict[str, str],
) -> tuple[Optional[str], Optional[Failed]]:
    try:
        return get_auth_token(config), None
    except Exception as e:
        err = f'Failed to obtain auth token: {repr(e)}'
        print(f'❌ {err}')
        for corp_num in corp_nums:
            tracking.update_corp_status(
                flow_run_id,
                corp_num,
                ProcessingStatuses.FAILED,
                error=err,
                **failure_actions,
            )
        return None, Failed(message=err)


def has_failed_action(result: dict, action_fields: tuple[str, ...]) -> bool:
    return any(result.get(field) == 'FAILED' for field in action_fields)


def update_auth_processing_from_task_result(
    *,
    tracking: ExtractTrackingService,
    flow_run_id,
    result: dict,
    status: ProcessingStatuses,
) -> None:
    tracking.update_corp_status(
        flow_run_id,
        result['corp_num'],
        status,
        error=result.get('error'),
        entity_action=result.get('entity_action'),
        contact_action=result.get('contact_action'),
        affiliation_action=result.get('affiliation_action'),
        invite_action=result.get('invite_action'),
        action_detail=result.get('action_detail'),
    )


def finalize_auth_task_results(
    *,
    tracking: ExtractTrackingService,
    flow_run_id,
    submitted: list[AuthSubmittedTask],
    status_action_fields: tuple[str, ...],
) -> AuthBatchFinalizationResult:
    if submitted:
        wait([item.future for item in submitted])

    component_operations: list[AuthComponentOperationRecord] = []
    failed_count = 0
    completed_count = 0

    for item in submitted:
        try:
            result = item.future.result()
        except Exception as e:
            err = task_result_error(e)
            tracking.update_corp_status(
                flow_run_id,
                item.corp_num,
                ProcessingStatuses.FAILED,
                error=err,
                **item.failure_actions,
            )
            failed_count += 1
            continue

        component_operations.extend(result.get('component_operations') or [])
        status = (
            ProcessingStatuses.FAILED
            if has_failed_action(result, status_action_fields)
            else ProcessingStatuses.COMPLETED
        )
        update_auth_processing_from_task_result(
            tracking=tracking,
            flow_run_id=flow_run_id,
            result=result,
            status=status,
        )

        if status == ProcessingStatuses.FAILED:
            failed_count += 1
        else:
            completed_count += 1

    return AuthBatchFinalizationResult(
        completed=completed_count,
        failed=failed_count,
        component_operations=component_operations,
    )


def insert_component_operations_or_failed(
    auth_tracking: AuthTrackingService,
    records: list[AuthComponentOperationRecord],
) -> Optional[Failed]:
    try:
        auth_tracking.insert_component_operations_required(records)
    except Exception as e:
        return Failed(message=f'Auth component-operation logging failed: {repr(e)}')
    return None
