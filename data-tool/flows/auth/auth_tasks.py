from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, List, Optional

from prefect import task
from prefect.cache_policies import NO_CACHE

from common.auth_service import AuthService
from .auth_flow_utils import auth_component_operation_logging_enabled
from .auth_models import AuthComponentStatus, AuthCreatePlan, AuthDeletePlan, AuthOperationScope, AuthProcessingIdentity
from .auth_tracking import AuthComponentOperationRecord


def parse_accounts_csv(csv_val: str | None) -> List[int]:
    """Parse a CSV list of account IDs into a sorted, de-duped list of ints."""
    if not csv_val:
        return []
    out: List[int] = []
    for tok in str(csv_val).split(','):
        t = tok.strip()
        if t.isdigit():
            out.append(int(t))
    return sorted(set(out))


def parse_corp_nums_csv(csv_val: str | None) -> List[str]:
    """Parse a CSV list of corp numbers into a de-duped list (preserving order)."""
    if not csv_val:
        return []
    parts: List[str] = []
    for tok in str(csv_val).replace('\n', ',').split(','):
        t = tok.strip().upper()
        if t:
            parts.append(t)
    seen = set()
    out: List[str] = []
    for t in parts:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _status_code(val: Any) -> int:
    try:
        return int(val)
    except Exception:
        return 0


def _truncate(val: str, max_len: int) -> str:
    if val is None:
        return ''
    if len(val) <= max_len:
        return val
    return val[: max_len - 3] + '...'


def _component_record_logging_enabled(
    config,
    *,
    auth_processing_id: Optional[int],
    identity: Optional[AuthProcessingIdentity],
    log_component_operations: Optional[bool],
) -> bool:
    """Return true only when task callers supplied enough identity to build records."""
    if auth_processing_id is None or identity is None:
        return False
    if log_component_operations is None:
        return auth_component_operation_logging_enabled(config)
    return bool(log_component_operations)


def _operation_detail(status: AuthComponentStatus, detail: str | None = None) -> str:
    parts = [f'result:{status.value}']
    if detail:
        parts.append(detail)
    return '; '.join(parts)


def _append_component_operation(
    records: Optional[List[AuthComponentOperationRecord]],
    *,
    auth_processing_id: int,
    corp_num: str,
    identity: AuthProcessingIdentity,
    flow_run_id,
    component: AuthOperationScope,
    target_type: str | None,
    target_value: Any = None,
    action: str,
    status: AuthComponentStatus,
    status_code: int | None = None,
    error: str | None = None,
    detail: str | None = None,
) -> None:
    """Append one safe component-operation record when logging is enabled.

    Do not pass passcodes, bearer tokens, or raw request/response payloads into this helper.
    """
    if records is None:
        return

    records.append(
        AuthComponentOperationRecord(
            auth_processing_id=auth_processing_id,
            corp_num=corp_num,
            flow_name=identity.flow_name,
            flow_run_id=flow_run_id,
            operation=identity.operation,
            operation_scope=identity.operation_scope,
            component=component,
            dry_run=identity.dry_run,
            target_type=target_type,
            target_value=str(target_value) if target_value is not None else None,
            action=action,
            status_code=status_code,
            error=error,
            detail=_operation_detail(status, detail),
        )
    )


def _auth_task_result(
    *,
    corp_num: str,
    entity_action: AuthComponentStatus,
    contact_action: AuthComponentStatus,
    affiliation_action: AuthComponentStatus,
    invite_action: AuthComponentStatus,
    action_detail: str,
    error: str | None,
    component_operations: Optional[List[AuthComponentOperationRecord]],
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        'corp_num': corp_num,
        'entity_action': entity_action.value,
        'contact_action': contact_action.value,
        'affiliation_action': affiliation_action.value,
        'invite_action': invite_action.value,
        'action_detail': action_detail,
        'error': error,
    }
    if component_operations is not None:
        result['component_operations'] = component_operations
    return result


@task(cache_policy=NO_CACHE)
def get_auth_token(config) -> str:
    """Get one bearer token to reuse for an entire claimed batch."""
    token = AuthService.get_bearer_token(config)
    if not token:
        raise Exception("Unable to obtain auth token")
    return token


@task(cache_policy=NO_CACHE)
def perform_auth_create_for_corp(
    config,
    corp_num: str,
    profile: Dict[str, Any],
    account_ids: List[int],
    plan: AuthCreatePlan,
    token: str,
    *,
    auth_processing_id: int | None = None,
    identity: AuthProcessingIdentity | None = None,
    flow_run_id=None,
    log_component_operations: bool | None = None,
) -> Dict[str, Any]:
    """
    Execute auth create-like operations for a single corp based on plan.

    Returns a dict suitable for persisting to auth_processing:
      - entity_action/contact_action/affiliation_action/invite_action
      - action_detail (short)
      - error (short, safe)
      - component_operations (optional, only when component logging inputs are supplied and enabled)
    """
    entity_action = AuthComponentStatus.NOT_RUN
    contact_action = AuthComponentStatus.NOT_RUN
    affiliation_action = AuthComponentStatus.NOT_RUN
    invite_action = AuthComponentStatus.NOT_RUN

    detail_parts: List[str] = []
    errors: List[str] = []
    current_operation: Optional[Dict[str, Any]] = None

    component_operations: Optional[List[AuthComponentOperationRecord]] = None
    if _component_record_logging_enabled(
        config,
        auth_processing_id=auth_processing_id,
        identity=identity,
        log_component_operations=log_component_operations,
    ):
        component_operations = []

    try:
        identifier = (profile or {}).get('identifier') or corp_num
        legal_name = (profile or {}).get('legal_name') or identifier
        legal_type = (profile or {}).get('legal_type') or (profile or {}).get('corp_type_cd') or ''

        # NEVER log or persist pass_code (secret).
        pass_code = (profile or {}).get('pass_code') or ''
        if getattr(config, 'USE_CUSTOM_PASSCODE', False) and getattr(config, 'CUSTOM_PASSCODE', ''):
            pass_code = getattr(config, 'CUSTOM_PASSCODE')

        # Determine contact email (safe to store)
        email = (profile or {}).get('admin_email') or (profile or {}).get('contact_email') or ''
        if getattr(config, 'USE_CUSTOM_CONTACT_EMAIL', False) and getattr(config, 'CUSTOM_CONTACT_EMAIL', ''):
            email = getattr(config, 'CUSTOM_CONTACT_EMAIL')

        # Mutual exclusion: affiliations vs invite
        if plan.create_affiliations and plan.send_unaffiliated_invite:
            affiliation_action = AuthComponentStatus.FAILED
            invite_action = AuthComponentStatus.FAILED
            errors.append('plan_conflict_affiliations_vs_invite')
            detail_parts.append('plan:invalid(affiliations+invite)')
            if auth_processing_id is not None and identity is not None:
                _append_component_operation(
                    component_operations,
                    auth_processing_id=auth_processing_id,
                    corp_num=corp_num,
                    identity=identity,
                    flow_run_id=flow_run_id,
                    component=AuthOperationScope.AFFILIATION,
                    target_type='account',
                    action='CREATE_AFFILIATION',
                    status=AuthComponentStatus.FAILED,
                    error='plan_conflict_affiliations_vs_invite',
                    detail='plan_conflict',
                )
                _append_component_operation(
                    component_operations,
                    auth_processing_id=auth_processing_id,
                    corp_num=corp_num,
                    identity=identity,
                    flow_run_id=flow_run_id,
                    component=AuthOperationScope.INVITE,
                    target_type='email',
                    target_value=email or None,
                    action='SEND_INVITE',
                    status=AuthComponentStatus.FAILED,
                    error='plan_conflict_affiliations_vs_invite',
                    detail='plan_conflict',
                )
            return _auth_task_result(
                corp_num=corp_num,
                entity_action=entity_action,
                contact_action=contact_action,
                affiliation_action=affiliation_action,
                invite_action=invite_action,
                action_detail=_truncate('; '.join(detail_parts), 2000),
                error=_truncate('; '.join(errors), 1000) or None,
                component_operations=component_operations,
            )

        # 1) Create entity
        explicit_entity_create_succeeded = False
        if plan.create_entity:
            if plan.dry_run:
                entity_action = AuthComponentStatus.SKIPPED
                detail_parts.append('entity:DRY_RUN')
                if auth_processing_id is not None and identity is not None:
                    _append_component_operation(
                        component_operations,
                        auth_processing_id=auth_processing_id,
                        corp_num=corp_num,
                        identity=identity,
                        flow_run_id=flow_run_id,
                        component=AuthOperationScope.ENTITY,
                        target_type='entity',
                        target_value=identifier,
                        action='CREATE_ENTITY',
                        status=AuthComponentStatus.SKIPPED,
                        detail='DRY_RUN',
                    )
            else:
                current_operation = {
                    'component': AuthOperationScope.ENTITY,
                    'target_type': 'entity',
                    'target_value': identifier,
                    'action': 'CREATE_ENTITY',
                }
                status = AuthService.create_entity(
                    config=config,
                    business_registration=identifier,
                    business_name=legal_name,
                    corp_type_code=legal_type,
                    pass_code=pass_code,
                    token=token
                )
                current_operation = None
                code = _status_code(status)
                detail_parts.append(f'entity:{code}')
                if code == int(HTTPStatus.OK):
                    entity_action = AuthComponentStatus.SUCCESS
                    explicit_entity_create_succeeded = True
                else:
                    entity_action = AuthComponentStatus.FAILED
                    errors.append(f'create_entity:{code}')
                if auth_processing_id is not None and identity is not None:
                    _append_component_operation(
                        component_operations,
                        auth_processing_id=auth_processing_id,
                        corp_num=corp_num,
                        identity=identity,
                        flow_run_id=flow_run_id,
                        component=AuthOperationScope.ENTITY,
                        target_type='entity',
                        target_value=identifier,
                        action='CREATE_ENTITY',
                        status=entity_action,
                        status_code=code,
                        error=None if entity_action == AuthComponentStatus.SUCCESS else f'create_entity:{code}',
                    )
                if entity_action == AuthComponentStatus.FAILED:
                    # Dependent create-side actions assume the explicit entity create succeeded.
                    # Do not call contact/affiliation/invite APIs after that failure; in
                    # particular avoid legacy create_affiliation(), which may create Auth side
                    # effects even though entity_action is already FAILED.
                    if plan.upsert_contact or plan.create_affiliations or plan.send_unaffiliated_invite:
                        detail_parts.append('dependent_actions:not_run_entity_failed')
                    return _auth_task_result(
                        corp_num=corp_num,
                        entity_action=entity_action,
                        contact_action=contact_action,
                        affiliation_action=affiliation_action,
                        invite_action=invite_action,
                        action_detail=_truncate('; '.join(detail_parts), 2000),
                        error=_truncate('; '.join(errors), 1000) or None,
                        component_operations=component_operations,
                    )

        # 2) Upsert contact
        if plan.upsert_contact:
            if not email:
                detail_parts.append('contact:missing_email')
                if plan.fail_if_missing_email:
                    contact_action = AuthComponentStatus.FAILED
                    errors.append('missing_email_for_contact')
                    contact_error = 'missing_email_for_contact'
                else:
                    contact_action = AuthComponentStatus.SKIPPED
                    contact_error = None
                if auth_processing_id is not None and identity is not None:
                    _append_component_operation(
                        component_operations,
                        auth_processing_id=auth_processing_id,
                        corp_num=corp_num,
                        identity=identity,
                        flow_run_id=flow_run_id,
                        component=AuthOperationScope.CONTACT,
                        target_type='email',
                        action='UPSERT_CONTACT',
                        status=contact_action,
                        error=contact_error,
                        detail='missing_email',
                    )
            elif plan.dry_run:
                contact_action = AuthComponentStatus.SKIPPED
                detail_parts.append('contact:DRY_RUN')
                if auth_processing_id is not None and identity is not None:
                    _append_component_operation(
                        component_operations,
                        auth_processing_id=auth_processing_id,
                        corp_num=corp_num,
                        identity=identity,
                        flow_run_id=flow_run_id,
                        component=AuthOperationScope.CONTACT,
                        target_type='email',
                        target_value=email,
                        action='UPSERT_CONTACT',
                        status=AuthComponentStatus.SKIPPED,
                        detail='DRY_RUN',
                    )
            else:
                current_operation = {
                    'component': AuthOperationScope.CONTACT,
                    'target_type': 'email',
                    'target_value': email,
                    'action': 'UPSERT_CONTACT',
                }
                status = AuthService.update_contact_email(
                    config=config,
                    identifier=identifier,
                    email=email,
                    token=token
                )
                current_operation = None
                code = _status_code(status)
                detail_parts.append(f'contact:{code}')
                if code == int(HTTPStatus.OK):
                    contact_action = AuthComponentStatus.SUCCESS
                else:
                    contact_action = AuthComponentStatus.FAILED
                    errors.append(f'upsert_contact:{code}')
                if auth_processing_id is not None and identity is not None:
                    _append_component_operation(
                        component_operations,
                        auth_processing_id=auth_processing_id,
                        corp_num=corp_num,
                        identity=identity,
                        flow_run_id=flow_run_id,
                        component=AuthOperationScope.CONTACT,
                        target_type='email',
                        target_value=email,
                        action='UPSERT_CONTACT',
                        status=contact_action,
                        status_code=code,
                        error=None if contact_action == AuthComponentStatus.SUCCESS else f'upsert_contact:{code}',
                    )

        # 3) Create affiliations
        if plan.create_affiliations:
            unique_accounts = sorted(set(account_ids))
            if not unique_accounts:
                affiliation_action = AuthComponentStatus.SKIPPED
                detail_parts.append('affiliations:no_accounts')
                if auth_processing_id is not None and identity is not None:
                    _append_component_operation(
                        component_operations,
                        auth_processing_id=auth_processing_id,
                        corp_num=corp_num,
                        identity=identity,
                        flow_run_id=flow_run_id,
                        component=AuthOperationScope.AFFILIATION,
                        target_type='account',
                        action='CREATE_AFFILIATION',
                        status=AuthComponentStatus.SKIPPED,
                        detail='no_accounts',
                    )
            elif plan.dry_run:
                affiliation_action = AuthComponentStatus.SKIPPED
                detail_parts.append(f'affiliations:DRY_RUN({len(unique_accounts)})')
                if auth_processing_id is not None and identity is not None:
                    for acct in unique_accounts:
                        _append_component_operation(
                            component_operations,
                            auth_processing_id=auth_processing_id,
                            corp_num=corp_num,
                            identity=identity,
                            flow_run_id=flow_run_id,
                            component=AuthOperationScope.AFFILIATION,
                            target_type='account',
                            target_value=acct,
                            action='CREATE_AFFILIATION',
                            status=AuthComponentStatus.SKIPPED,
                            detail='DRY_RUN',
                        )
            else:
                ok = 0
                fail = 0
                for acct in unique_accounts:
                    current_operation = {
                        'component': AuthOperationScope.AFFILIATION,
                        'target_type': 'account',
                        'target_value': acct,
                        'action': 'CREATE_AFFILIATION',
                    }
                    use_affiliation_only = explicit_entity_create_succeeded or not plan.allow_entity_creation_for_affiliations
                    if use_affiliation_only:
                        status = AuthService.create_affiliation_only(
                            config=config,
                            account=acct,
                            business_registration=identifier,
                            pass_code=pass_code,
                            details={'identifier': identifier},
                            token=token
                        )
                    else:
                        # Preserve legacy idempotent fallback when entity creation is allowed by the caller.
                        status = AuthService.create_affiliation(
                            config=config,
                            account=acct,
                            business_registration=identifier,
                            business_name=legal_name,
                            corp_type_code=legal_type,
                            pass_code=pass_code,
                            details={'identifier': identifier},
                            token=token
                        )
                    current_operation = None
                    code = _status_code(status)
                    if code == int(HTTPStatus.OK):
                        ok += 1
                        affiliation_status = AuthComponentStatus.SUCCESS
                    else:
                        fail += 1
                        affiliation_status = AuthComponentStatus.FAILED
                    if auth_processing_id is not None and identity is not None:
                        _append_component_operation(
                            component_operations,
                            auth_processing_id=auth_processing_id,
                            corp_num=corp_num,
                            identity=identity,
                            flow_run_id=flow_run_id,
                            component=AuthOperationScope.AFFILIATION,
                            target_type='account',
                            target_value=acct,
                            action='CREATE_AFFILIATION',
                            status=affiliation_status,
                            status_code=code,
                            error=None if affiliation_status == AuthComponentStatus.SUCCESS else f'create_affiliation:{code}',
                            detail='affiliation_only' if use_affiliation_only else 'legacy_create_affiliation',
                        )
                detail_parts.append(f'affiliations:ok{ok} fail{fail}')
                if fail > 0:
                    affiliation_action = AuthComponentStatus.FAILED
                    errors.append(f'create_affiliations_failed:{fail}')
                else:
                    affiliation_action = AuthComponentStatus.SUCCESS

        # 4) Send unaffiliated invite
        if plan.send_unaffiliated_invite:
            if not email:
                detail_parts.append('invite:missing_email')
                if plan.fail_if_missing_email:
                    invite_action = AuthComponentStatus.FAILED
                    errors.append('missing_email_for_invite')
                    invite_error = 'missing_email_for_invite'
                else:
                    invite_action = AuthComponentStatus.SKIPPED
                    invite_error = None
                if auth_processing_id is not None and identity is not None:
                    _append_component_operation(
                        component_operations,
                        auth_processing_id=auth_processing_id,
                        corp_num=corp_num,
                        identity=identity,
                        flow_run_id=flow_run_id,
                        component=AuthOperationScope.INVITE,
                        target_type='email',
                        action='SEND_INVITE',
                        status=invite_action,
                        error=invite_error,
                        detail='missing_email',
                    )
            elif plan.dry_run:
                invite_action = AuthComponentStatus.SKIPPED
                detail_parts.append('invite:DRY_RUN')
                if auth_processing_id is not None and identity is not None:
                    _append_component_operation(
                        component_operations,
                        auth_processing_id=auth_processing_id,
                        corp_num=corp_num,
                        identity=identity,
                        flow_run_id=flow_run_id,
                        component=AuthOperationScope.INVITE,
                        target_type='email',
                        target_value=email,
                        action='SEND_INVITE',
                        status=AuthComponentStatus.SKIPPED,
                        detail='DRY_RUN',
                    )
            else:
                current_operation = {
                    'component': AuthOperationScope.INVITE,
                    'target_type': 'email',
                    'target_value': email,
                    'action': 'SEND_INVITE',
                }
                status = AuthService.send_unaffiliated_email(
                    config=config,
                    identifier=identifier,
                    email=email,
                    token=token
                )
                current_operation = None
                code = _status_code(status)
                detail_parts.append(f'invite:{code}')
                if code == int(HTTPStatus.OK):
                    invite_action = AuthComponentStatus.SUCCESS
                else:
                    invite_action = AuthComponentStatus.FAILED
                    errors.append(f'send_invite:{code}')
                if auth_processing_id is not None and identity is not None:
                    _append_component_operation(
                        component_operations,
                        auth_processing_id=auth_processing_id,
                        corp_num=corp_num,
                        identity=identity,
                        flow_run_id=flow_run_id,
                        component=AuthOperationScope.INVITE,
                        target_type='email',
                        target_value=email,
                        action='SEND_INVITE',
                        status=invite_action,
                        status_code=code,
                        error=None if invite_action == AuthComponentStatus.SUCCESS else f'send_invite:{code}',
                    )

    except Exception as e:
        detail_parts.append('exception')
        exception_error = _truncate(repr(e), 900)
        errors.append(exception_error)
        if current_operation and auth_processing_id is not None and identity is not None:
            _append_component_operation(
                component_operations,
                auth_processing_id=auth_processing_id,
                corp_num=corp_num,
                identity=identity,
                flow_run_id=flow_run_id,
                status=AuthComponentStatus.FAILED,
                error=exception_error,
                detail='exception',
                **current_operation,
            )
        if plan.create_entity and entity_action == AuthComponentStatus.NOT_RUN:
            entity_action = AuthComponentStatus.FAILED
        if plan.upsert_contact and contact_action == AuthComponentStatus.NOT_RUN:
            contact_action = AuthComponentStatus.FAILED
        if plan.create_affiliations and affiliation_action == AuthComponentStatus.NOT_RUN:
            affiliation_action = AuthComponentStatus.FAILED
        if plan.send_unaffiliated_invite and invite_action == AuthComponentStatus.NOT_RUN:
            invite_action = AuthComponentStatus.FAILED

    action_detail = _truncate('; '.join(detail_parts), 2000)
    error = _truncate('; '.join(errors), 1000) if errors else None

    return _auth_task_result(
        corp_num=corp_num,
        entity_action=entity_action,
        contact_action=contact_action,
        affiliation_action=affiliation_action,
        invite_action=invite_action,
        action_detail=action_detail,
        error=error,
        component_operations=component_operations,
    )


@task(cache_policy=NO_CACHE)
def perform_auth_delete_for_corp(
    config,
    corp_num: str,
    account_ids: List[int],
    plan: AuthDeletePlan,
    token: str,
    *,
    auth_processing_id: int | None = None,
    identity: AuthProcessingIdentity | None = None,
    flow_run_id=None,
    log_component_operations: bool | None = None,
) -> Dict[str, Any]:
    """
    Execute auth delete-like operations for a single corp based on plan.

    IMPORTANT: Uses explicit delete primitives (no combined delete_affiliation()).

    Returns a dict suitable for persisting to auth_processing.
    """
    identifier = corp_num

    entity_action = AuthComponentStatus.NOT_RUN
    contact_action = AuthComponentStatus.NOT_RUN
    affiliation_action = AuthComponentStatus.NOT_RUN
    invite_action = AuthComponentStatus.NOT_RUN

    detail_parts: List[str] = []
    errors: List[str] = []
    current_operation: Optional[Dict[str, Any]] = None

    component_operations: Optional[List[AuthComponentOperationRecord]] = None
    if _component_record_logging_enabled(
        config,
        auth_processing_id=auth_processing_id,
        identity=identity,
        log_component_operations=log_component_operations,
    ):
        component_operations = []

    try:
        # 1) Delete affiliations (best-effort across accounts)
        if plan.delete_affiliations:
            unique_accounts = sorted(set(account_ids))
            if not unique_accounts:
                affiliation_action = AuthComponentStatus.SKIPPED
                detail_parts.append('del_affiliations:no_accounts')
                if auth_processing_id is not None and identity is not None:
                    _append_component_operation(
                        component_operations,
                        auth_processing_id=auth_processing_id,
                        corp_num=corp_num,
                        identity=identity,
                        flow_run_id=flow_run_id,
                        component=AuthOperationScope.AFFILIATION,
                        target_type='account',
                        action='DELETE_AFFILIATION',
                        status=AuthComponentStatus.SKIPPED,
                        detail='no_accounts',
                    )
            elif plan.dry_run:
                affiliation_action = AuthComponentStatus.SKIPPED
                detail_parts.append(f'del_affiliations:DRY_RUN({len(unique_accounts)})')
                if auth_processing_id is not None and identity is not None:
                    for acct in unique_accounts:
                        _append_component_operation(
                            component_operations,
                            auth_processing_id=auth_processing_id,
                            corp_num=corp_num,
                            identity=identity,
                            flow_run_id=flow_run_id,
                            component=AuthOperationScope.AFFILIATION,
                            target_type='account',
                            target_value=acct,
                            action='DELETE_AFFILIATION',
                            status=AuthComponentStatus.SKIPPED,
                            detail='DRY_RUN',
                        )
            else:
                ok = 0
                not_found = 0
                fail = 0
                for acct in unique_accounts:
                    current_operation = {
                        'component': AuthOperationScope.AFFILIATION,
                        'target_type': 'account',
                        'target_value': acct,
                        'action': 'DELETE_AFFILIATION',
                    }
                    status = AuthService.delete_affiliation_only(
                        config=config,
                        account=acct,
                        identifier=identifier,
                        token=token
                    )
                    current_operation = None
                    code = _status_code(status)
                    if code in (int(HTTPStatus.OK), int(HTTPStatus.NO_CONTENT)):
                        ok += 1
                        affiliation_status = AuthComponentStatus.SUCCESS
                    elif code == int(HTTPStatus.NOT_FOUND):
                        not_found += 1
                        affiliation_status = AuthComponentStatus.SKIPPED
                    else:
                        fail += 1
                        affiliation_status = AuthComponentStatus.FAILED
                    if auth_processing_id is not None and identity is not None:
                        _append_component_operation(
                            component_operations,
                            auth_processing_id=auth_processing_id,
                            corp_num=corp_num,
                            identity=identity,
                            flow_run_id=flow_run_id,
                            component=AuthOperationScope.AFFILIATION,
                            target_type='account',
                            target_value=acct,
                            action='DELETE_AFFILIATION',
                            status=affiliation_status,
                            status_code=code,
                            error=None if affiliation_status != AuthComponentStatus.FAILED else f'delete_affiliation:{code}',
                        )

                detail_parts.append(f'del_affiliations:ok{ok} nf{not_found} fail{fail}')
                if fail > 0:
                    affiliation_action = AuthComponentStatus.FAILED
                    errors.append(f'delete_affiliations_failed:{fail}')
                elif ok > 0:
                    affiliation_action = AuthComponentStatus.SUCCESS
                else:
                    affiliation_action = AuthComponentStatus.SKIPPED

        # 2) Delete entity (after affiliations)
        if plan.delete_entity:
            if plan.dry_run:
                entity_action = AuthComponentStatus.SKIPPED
                detail_parts.append('del_entity:DRY_RUN')
                if auth_processing_id is not None and identity is not None:
                    _append_component_operation(
                        component_operations,
                        auth_processing_id=auth_processing_id,
                        corp_num=corp_num,
                        identity=identity,
                        flow_run_id=flow_run_id,
                        component=AuthOperationScope.ENTITY,
                        target_type='entity',
                        target_value=identifier,
                        action='DELETE_ENTITY',
                        status=AuthComponentStatus.SKIPPED,
                        detail='DRY_RUN',
                    )
            else:
                current_operation = {
                    'component': AuthOperationScope.ENTITY,
                    'target_type': 'entity',
                    'target_value': identifier,
                    'action': 'DELETE_ENTITY',
                }
                status = AuthService.delete_entity(
                    config=config,
                    identifier=identifier,
                    token=token
                )
                current_operation = None
                code = _status_code(status)
                detail_parts.append(f'del_entity:{code}')
                if code in (int(HTTPStatus.OK), int(HTTPStatus.NO_CONTENT)):
                    entity_action = AuthComponentStatus.SUCCESS
                elif code == int(HTTPStatus.NOT_FOUND):
                    entity_action = AuthComponentStatus.SKIPPED
                else:
                    entity_action = AuthComponentStatus.FAILED
                    errors.append(f'delete_entity:{code}')
                if auth_processing_id is not None and identity is not None:
                    _append_component_operation(
                        component_operations,
                        auth_processing_id=auth_processing_id,
                        corp_num=corp_num,
                        identity=identity,
                        flow_run_id=flow_run_id,
                        component=AuthOperationScope.ENTITY,
                        target_type='entity',
                        target_value=identifier,
                        action='DELETE_ENTITY',
                        status=entity_action,
                        status_code=code,
                        error=None if entity_action != AuthComponentStatus.FAILED else f'delete_entity:{code}',
                    )

    except Exception as e:
        detail_parts.append('exception')
        exception_error = _truncate(repr(e), 900)
        errors.append(exception_error)
        if current_operation and auth_processing_id is not None and identity is not None:
            _append_component_operation(
                component_operations,
                auth_processing_id=auth_processing_id,
                corp_num=corp_num,
                identity=identity,
                flow_run_id=flow_run_id,
                status=AuthComponentStatus.FAILED,
                error=exception_error,
                detail='exception',
                **current_operation,
            )
        if plan.delete_affiliations and affiliation_action == AuthComponentStatus.NOT_RUN:
            affiliation_action = AuthComponentStatus.FAILED
        if plan.delete_entity and entity_action == AuthComponentStatus.NOT_RUN:
            entity_action = AuthComponentStatus.FAILED

    action_detail = _truncate('; '.join(detail_parts), 2000)
    error = _truncate('; '.join(errors), 1000) if errors else None

    return _auth_task_result(
        corp_num=corp_num,
        entity_action=entity_action,
        contact_action=contact_action,
        affiliation_action=affiliation_action,
        invite_action=invite_action,
        action_detail=action_detail,
        error=error,
        component_operations=component_operations,
    )
