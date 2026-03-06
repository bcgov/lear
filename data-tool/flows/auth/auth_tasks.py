from __future__ import annotations

from http import HTTPStatus
from typing import Any, Dict, List

from prefect import task
from prefect.cache_policies import NO_CACHE

from common.auth_service import AuthService
from .auth_models import AuthComponentStatus, AuthCreatePlan, AuthDeletePlan


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
    token: str
) -> Dict[str, Any]:
    """
    Execute auth create-like operations for a single corp based on plan.

    Returns a dict suitable for persisting to auth_processing:
      - entity_action/contact_action/affiliation_action/invite_action
      - action_detail (short)
      - error (short, safe)
    """
    entity_action = AuthComponentStatus.NOT_RUN
    contact_action = AuthComponentStatus.NOT_RUN
    affiliation_action = AuthComponentStatus.NOT_RUN
    invite_action = AuthComponentStatus.NOT_RUN

    detail_parts: List[str] = []
    errors: List[str] = []

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
            return {
                'corp_num': corp_num,
                'entity_action': entity_action.value,
                'contact_action': contact_action.value,
                'affiliation_action': affiliation_action.value,
                'invite_action': invite_action.value,
                'action_detail': _truncate('; '.join(detail_parts), 2000),
                'error': _truncate('; '.join(errors), 1000) or None
            }

        # 1) Create entity
        if plan.create_entity:
            if plan.dry_run:
                entity_action = AuthComponentStatus.SKIPPED
                detail_parts.append('entity:DRY_RUN')
            else:
                status = AuthService.create_entity(
                    config=config,
                    business_registration=identifier,
                    business_name=legal_name,
                    corp_type_code=legal_type,
                    pass_code=pass_code,
                    token=token
                )
                code = _status_code(status)
                detail_parts.append(f'entity:{code}')
                if code == int(HTTPStatus.OK):
                    entity_action = AuthComponentStatus.SUCCESS
                else:
                    entity_action = AuthComponentStatus.FAILED
                    errors.append(f'create_entity:{code}')

        # 2) Upsert contact
        if plan.upsert_contact:
            if not email:
                detail_parts.append('contact:missing_email')
                if plan.fail_if_missing_email:
                    contact_action = AuthComponentStatus.FAILED
                    errors.append('missing_email_for_contact')
                else:
                    contact_action = AuthComponentStatus.SKIPPED
            elif plan.dry_run:
                contact_action = AuthComponentStatus.SKIPPED
                detail_parts.append('contact:DRY_RUN')
            else:
                status = AuthService.update_contact_email(
                    config=config,
                    identifier=identifier,
                    email=email,
                    token=token
                )
                code = _status_code(status)
                detail_parts.append(f'contact:{code}')
                if code == int(HTTPStatus.OK):
                    contact_action = AuthComponentStatus.SUCCESS
                else:
                    contact_action = AuthComponentStatus.FAILED
                    errors.append(f'upsert_contact:{code}')

        # 3) Create affiliations
        if plan.create_affiliations:
            if not account_ids:
                affiliation_action = AuthComponentStatus.SKIPPED
                detail_parts.append('affiliations:no_accounts')
            elif plan.dry_run:
                affiliation_action = AuthComponentStatus.SKIPPED
                detail_parts.append(f'affiliations:DRY_RUN({len(account_ids)})')
            else:
                ok = 0
                fail = 0
                for acct in sorted(set(account_ids)):
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
                    code = _status_code(status)
                    if code == int(HTTPStatus.OK):
                        ok += 1
                    else:
                        fail += 1
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
                else:
                    invite_action = AuthComponentStatus.SKIPPED
            elif plan.dry_run:
                invite_action = AuthComponentStatus.SKIPPED
                detail_parts.append('invite:DRY_RUN')
            else:
                status = AuthService.send_unaffiliated_email(
                    config=config,
                    identifier=identifier,
                    email=email,
                    token=token
                )
                code = _status_code(status)
                detail_parts.append(f'invite:{code}')
                if code == int(HTTPStatus.OK):
                    invite_action = AuthComponentStatus.SUCCESS
                else:
                    invite_action = AuthComponentStatus.FAILED
                    errors.append(f'send_invite:{code}')

    except Exception as e:
        detail_parts.append('exception')
        errors.append(_truncate(repr(e), 900))
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

    return {
        'corp_num': corp_num,
        'entity_action': entity_action.value,
        'contact_action': contact_action.value,
        'affiliation_action': affiliation_action.value,
        'invite_action': invite_action.value,
        'action_detail': action_detail,
        'error': error
    }


@task(cache_policy=NO_CACHE)
def perform_auth_delete_for_corp(
    config,
    corp_num: str,
    account_ids: List[int],
    plan: AuthDeletePlan,
    token: str
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

    try:
        # 1) Delete affiliations (best-effort across accounts)
        if plan.delete_affiliations:
            if not account_ids:
                affiliation_action = AuthComponentStatus.SKIPPED
                detail_parts.append('del_affiliations:no_accounts')
            elif plan.dry_run:
                affiliation_action = AuthComponentStatus.SKIPPED
                detail_parts.append(f'del_affiliations:DRY_RUN({len(account_ids)})')
            else:
                ok = 0
                not_found = 0
                fail = 0
                for acct in sorted(set(account_ids)):
                    status = AuthService.delete_affiliation_only(
                        config=config,
                        account=acct,
                        identifier=identifier,
                        token=token
                    )
                    code = _status_code(status)
                    if code in (int(HTTPStatus.OK), int(HTTPStatus.NO_CONTENT)):
                        ok += 1
                    elif code == int(HTTPStatus.NOT_FOUND):
                        not_found += 1
                    else:
                        fail += 1

                detail_parts.append(f'del_affiliations:ok{ok} nf{not_found} fail{fail}')
                if fail > 0:
                    affiliation_action = AuthComponentStatus.FAILED
                    errors.append(f'delete_affiliations_failed:{fail}')
                elif ok > 0:
                    affiliation_action = AuthComponentStatus.SUCCESS
                else:
                    affiliation_action = AuthComponentStatus.SKIPPED

        # 2) Delete invites (NOT supported by current client/API)
        if plan.delete_invites:
            invite_action = AuthComponentStatus.FAILED
            detail_parts.append('del_invites:UNSUPPORTED')
            errors.append('delete_invites_not_supported')

        # 3) Delete entity (after affiliations)
        if plan.delete_entity:
            if plan.dry_run:
                entity_action = AuthComponentStatus.SKIPPED
                detail_parts.append('del_entity:DRY_RUN')
            else:
                status = AuthService.delete_entity(
                    config=config,
                    identifier=identifier,
                    token=token
                )
                code = _status_code(status)
                detail_parts.append(f'del_entity:{code}')
                if code in (int(HTTPStatus.OK), int(HTTPStatus.NO_CONTENT)):
                    entity_action = AuthComponentStatus.SUCCESS
                elif code == int(HTTPStatus.NOT_FOUND):
                    entity_action = AuthComponentStatus.SKIPPED
                else:
                    entity_action = AuthComponentStatus.FAILED
                    errors.append(f'delete_entity:{code}')

    except Exception as e:
        detail_parts.append('exception')
        errors.append(_truncate(repr(e), 900))
        if plan.delete_affiliations and affiliation_action == AuthComponentStatus.NOT_RUN:
            affiliation_action = AuthComponentStatus.FAILED
        if plan.delete_invites and invite_action == AuthComponentStatus.NOT_RUN:
            invite_action = AuthComponentStatus.FAILED
        if plan.delete_entity and entity_action == AuthComponentStatus.NOT_RUN:
            entity_action = AuthComponentStatus.FAILED

    action_detail = _truncate('; '.join(detail_parts), 2000)
    error = _truncate('; '.join(errors), 1000) if errors else None

    return {
        'corp_num': corp_num,
        'entity_action': entity_action.value,
        'contact_action': contact_action.value,
        'affiliation_action': affiliation_action.value,
        'invite_action': invite_action.value,
        'action_detail': action_detail,
        'error': error
    }
