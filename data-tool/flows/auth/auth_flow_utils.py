from __future__ import annotations

import hashlib
from typing import Optional, Sequence

from .auth_models import (
    AuthDeletePlan,
    AuthOperation,
    AuthOperationScope,
    AuthProcessingIdentity,
    AuthRepeatability,
    AuthRepeatableCampaign,
)

AUTH_CREATE_FLOW_NAME = 'auth-create-flow'
AUTH_CONTACT_FLOW_NAME = 'auth-contact-flow'
AUTH_AFFILIATION_CREATE_FLOW_NAME = 'auth-affiliation-create-flow'
AUTH_INVITE_FLOW_NAME = 'auth-invite-flow'
AUTH_DELETE_FLOW_NAME = 'auth-delete-flow'

AUTH_PROCESSING_IDENTITY_CONFLICT_COLUMNS: Sequence[str] = (
    'corp_num',
    'flow_name',
    'environment',
    'operation',
    'operation_scope',
    'attempt_key',
)


def _flow_run_id_text(flow_run_id) -> str:
    """Return flow_run_id text, raising when an attempt-specific key needs one."""
    value = str(flow_run_id or '').strip()
    if not value:
        raise ValueError('flow_run_id is required to build auth attempt identity')
    return value


def build_auth_attempt_key_from_context(attempt_key_context: str) -> str:
    """Build the hash-only auth_processing attempt_key from its canonical text context."""
    if not isinstance(attempt_key_context, str) or not attempt_key_context:
        raise ValueError('attempt_key_context is required to build auth attempt identity')
    digest = hashlib.sha256(attempt_key_context.encode('utf-8')).hexdigest()
    return f'ATTEMPT:v1:{digest}'


def build_auth_attempt_key_context(
    *,
    flow_name: str,
    operation: AuthOperation,
    operation_scope: AuthOperationScope,
    repeatability: AuthRepeatability,
    flow_run_id,
    dry_run: bool = False,
    campaign: Optional[AuthRepeatableCampaign] = None,
) -> str:
    """Build the canonical readable preimage for auth_processing attempt identity."""
    operation_value = AuthOperation(operation).value
    scope_value = AuthOperationScope(operation_scope).value

    if dry_run:
        return f'DRY_RUN:v1:{flow_name}:{operation_value}:{scope_value}:{_flow_run_id_text(flow_run_id)}'
    if repeatability == AuthRepeatability.ONE_SHOT:
        return f'ONE_SHOT:v1:{flow_name}:{operation_value}:{scope_value}'
    if repeatability == AuthRepeatability.REPEATABLE:
        if campaign is None:
            raise ValueError('campaign is required for non-dry-run repeatable auth identity')
        return campaign.attempt_key_context
    if repeatability == AuthRepeatability.RESET:
        if campaign is not None:
            return campaign.attempt_key_context
        return f'RESET:v1:{flow_name}:{operation_value}:{scope_value}'
    raise ValueError(f'Unsupported auth repeatability: {repeatability}')


def build_auth_processing_identity(
    *,
    flow_name: str,
    operation: AuthOperation,
    operation_scope: AuthOperationScope,
    repeatability: AuthRepeatability,
    flow_run_id,
    dry_run: bool = False,
    campaign: Optional[AuthRepeatableCampaign] = None,
    operation_target: Optional[str] = None,
    full_reset_sweep: bool = False,
) -> AuthProcessingIdentity:
    """Create an AuthProcessingIdentity with the correct attempt key."""
    if (
        repeatability in (AuthRepeatability.REPEATABLE, AuthRepeatability.RESET)
        and not dry_run
        and campaign is not None
        and operation_target is None
    ):
        operation_target = campaign.operation_target

    attempt_key_context = build_auth_attempt_key_context(
        flow_name=flow_name,
        operation=operation,
        operation_scope=operation_scope,
        repeatability=repeatability,
        flow_run_id=flow_run_id,
        dry_run=dry_run,
        campaign=campaign,
    )

    return AuthProcessingIdentity(
        flow_name=flow_name,
        operation=operation,
        operation_scope=operation_scope,
        repeatability=repeatability,
        attempt_key_context=attempt_key_context,
        attempt_key=build_auth_attempt_key_from_context(attempt_key_context),
        dry_run=dry_run,
        operation_target=operation_target,
        full_reset_sweep=full_reset_sweep,
    )


def auth_create_identity(flow_run_id, *, dry_run: bool = False) -> AuthProcessingIdentity:
    """Identity for the one-shot Auth entity create flow."""
    return build_auth_processing_identity(
        flow_name=AUTH_CREATE_FLOW_NAME,
        operation=AuthOperation.CREATE,
        operation_scope=AuthOperationScope.ENTITY,
        repeatability=AuthRepeatability.ONE_SHOT,
        flow_run_id=flow_run_id,
        dry_run=dry_run,
    )


def auth_contact_identity(
    flow_run_id,
    *,
    dry_run: bool = False,
    campaign: Optional[AuthRepeatableCampaign] = None,
    operation_target: Optional[str] = None,
) -> AuthProcessingIdentity:
    """Identity for repeatable Auth contact upsert runs."""
    return build_auth_processing_identity(
        flow_name=AUTH_CONTACT_FLOW_NAME,
        operation=AuthOperation.UPSERT,
        operation_scope=AuthOperationScope.CONTACT,
        repeatability=AuthRepeatability.REPEATABLE,
        flow_run_id=flow_run_id,
        dry_run=dry_run,
        campaign=campaign,
        operation_target=operation_target,
    )


def auth_affiliation_identity(
    flow_run_id,
    *,
    dry_run: bool = False,
    campaign: Optional[AuthRepeatableCampaign] = None,
    operation_target: Optional[str] = None,
) -> AuthProcessingIdentity:
    """Identity for repeatable affiliation create runs."""
    return build_auth_processing_identity(
        flow_name=AUTH_AFFILIATION_CREATE_FLOW_NAME,
        operation=AuthOperation.CREATE,
        operation_scope=AuthOperationScope.AFFILIATION,
        repeatability=AuthRepeatability.REPEATABLE,
        flow_run_id=flow_run_id,
        dry_run=dry_run,
        campaign=campaign,
        operation_target=operation_target,
    )


def auth_invite_identity(
    flow_run_id,
    *,
    dry_run: bool = False,
    campaign: Optional[AuthRepeatableCampaign] = None,
    operation_target: Optional[str] = None,
) -> AuthProcessingIdentity:
    """Identity for repeatable unaffiliated invite sends."""
    return build_auth_processing_identity(
        flow_name=AUTH_INVITE_FLOW_NAME,
        operation=AuthOperation.SEND,
        operation_scope=AuthOperationScope.INVITE,
        repeatability=AuthRepeatability.REPEATABLE,
        flow_run_id=flow_run_id,
        dry_run=dry_run,
        campaign=campaign,
        operation_target=operation_target,
    )


def auth_delete_identity(
    plan: AuthDeletePlan,
    flow_run_id,
    *,
    campaign: Optional[AuthRepeatableCampaign] = None,
    operation_target: Optional[str] = None,
) -> AuthProcessingIdentity:
    """Identity for supported Auth delete flow modes.

    Full entity delete uses RESET/FULL_ENTITY. Affiliation-only delete remains repeatable.
    """
    if not (plan.delete_entity or plan.delete_affiliations):
        raise ValueError('At least one auth delete operation must be selected')

    if plan.delete_entity:
        return build_auth_processing_identity(
            flow_name=AUTH_DELETE_FLOW_NAME,
            operation=AuthOperation.RESET,
            operation_scope=AuthOperationScope.FULL_ENTITY,
            repeatability=AuthRepeatability.RESET,
            flow_run_id=flow_run_id,
            dry_run=plan.dry_run,
            campaign=campaign,
            operation_target=operation_target,
            full_reset_sweep=bool(campaign is not None and not plan.dry_run),
        )

    return build_auth_processing_identity(
        flow_name=AUTH_DELETE_FLOW_NAME,
        operation=AuthOperation.DELETE,
        operation_scope=AuthOperationScope.AFFILIATION,
        repeatability=AuthRepeatability.REPEATABLE,
        flow_run_id=flow_run_id,
        dry_run=plan.dry_run,
        campaign=campaign,
        operation_target=operation_target,
    )


def _config_bool(config, attr: str, default: bool) -> bool:
    """Return a bool config value, accepting real bools and env-style strings."""
    value = getattr(config, attr, default)
    if isinstance(value, str):
        return value.strip().lower() == 'true'
    if value is None:
        return default
    return bool(value)


def auth_component_operation_logging_enabled(config) -> bool:
    """Return whether component-operation logging is enabled; defaults to false."""
    return _config_bool(config, 'AUTH_LOG_COMPONENT_OPERATIONS', False)
