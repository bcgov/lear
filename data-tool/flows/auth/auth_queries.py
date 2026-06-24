from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from .auth_flow_utils import auth_custom_contact_email_override
from .auth_models import (
    AuthProcessingIdentity,
    AuthRepeatability,
    AuthSelectionMode,
)
from .auth_selection import (
    auth_migration_filter_ids,
    parse_auth_corp_nums_csv,
    positive_int_csv_for_sql,
)

# Match the existing tombstone corp type cohort by default.
CORP_TYPE_FILTER = "('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')"
_UNSET = object()


def _escape_sql_literal(val: str) -> str:
    """Escape a value for safe embedding in a SQL single-quoted literal."""
    return (val or "").replace("'", "''")


def _quote_list(values: Sequence[str]) -> str:
    """Quote/escape a list of values for SQL IN (...) lists."""
    return ", ".join([f"'{_escape_sql_literal(v)}'" for v in values])


def get_auth_query_params(
    identity: Optional[AuthProcessingIdentity],
    *,
    config=None,
    include_contact_email: bool = False,
) -> Dict[str, object]:
    """Return bind parameters required by auth query predicates/select columns."""
    params: Dict[str, object] = {}
    uses_auth_attempt_key = (
        identity is not None
        and not identity.dry_run
        and (
            identity.repeatability == AuthRepeatability.REPEATABLE
            or (
                identity.repeatability == AuthRepeatability.RESET
                and identity.full_reset_sweep
            )
        )
    )
    if uses_auth_attempt_key:
        params['auth_attempt_key'] = identity.attempt_key

    custom_contact_email = (
        auth_custom_contact_email_override(config)
        if config is not None and include_contact_email
        else None
    )
    if custom_contact_email is not None:
        params['auth_custom_contact_email'] = custom_contact_email

    return params


def _auth_processing_exclusion_sql(
    *,
    flow_name: str,
    environment: str,
    identity: Optional[AuthProcessingIdentity],
) -> tuple[str, str]:
    """Return auth_processing join/predicate SQL for the selection policy.

    Legacy callers that have not yet been updated to pass an AuthProcessingIdentity retain
    the old one-row-per-(corp, flow, environment) anti-join behavior. Identity-aware callers
    get policy-driven blocking:
      - active non-dry-run rows for the same corp/environment block all auth flows, including dry-runs;
      - ONE_SHOT and RESET real runs also exclude historical non-dry-run rows for the same operation/scope;
      - real REPEATABLE rows exclude same-cycle attempts by attempt_key, regardless of status;
      - older-cycle REPEATABLE history only contributes to priority ordering.
    """
    flow_sql = _escape_sql_literal(flow_name)
    env_sql = _escape_sql_literal(environment)

    if identity is None:
        legacy_join = f"""
    LEFT JOIN auth_processing ap
        ON ap.corp_num = c.corp_num
       AND ap.flow_name = '{flow_sql}'
       AND ap.environment = '{env_sql}'
    """
        return legacy_join, "AND ap.corp_num IS NULL"

    if identity.flow_name != flow_name:
        raise ValueError(
            f'flow_name ({flow_name}) must match identity.flow_name ({identity.flow_name})'
        )

    if identity.repeatability not in (
        AuthRepeatability.ONE_SHOT,
        AuthRepeatability.RESET,
        AuthRepeatability.REPEATABLE,
    ):
        raise ValueError(f'Unsupported auth repeatability: {identity.repeatability}')

    operation_sql = _escape_sql_literal(identity.operation.value)
    scope_sql = _escape_sql_literal(identity.operation_scope.value)

    exclusion = f"""
        AND NOT EXISTS (
            SELECT 1
            FROM auth_processing ap_active
            WHERE ap_active.corp_num = c.corp_num
              AND ap_active.environment = '{env_sql}'
              AND COALESCE(ap_active.dry_run, false) = false
              AND ap_active.processed_status IN ('PENDING', 'PROCESSING')
        )
    """

    if identity.dry_run:
        return "", exclusion

    if identity.repeatability == AuthRepeatability.RESET and identity.full_reset_sweep:
        exclusion += f"""
        AND NOT EXISTS (
            SELECT 1
            FROM auth_processing ap_reset_sweep
            WHERE ap_reset_sweep.corp_num = c.corp_num
              AND ap_reset_sweep.flow_name = '{flow_sql}'
              AND ap_reset_sweep.environment = '{env_sql}'
              AND ap_reset_sweep.operation = '{operation_sql}'
              AND ap_reset_sweep.operation_scope = '{scope_sql}'
              AND ap_reset_sweep.attempt_key = :auth_attempt_key
              AND COALESCE(ap_reset_sweep.dry_run, false) = false
        )
        AND NOT EXISTS (
            SELECT 1
            FROM auth_processing ap_reset_failed
            WHERE ap_reset_failed.corp_num = c.corp_num
              AND ap_reset_failed.flow_name = '{flow_sql}'
              AND ap_reset_failed.environment = '{env_sql}'
              AND ap_reset_failed.operation = '{operation_sql}'
              AND ap_reset_failed.operation_scope = '{scope_sql}'
              AND ap_reset_failed.processed_status = 'FAILED'
              AND COALESCE(ap_reset_failed.dry_run, false) = false
        )
        """

    if identity.repeatability in (AuthRepeatability.ONE_SHOT, AuthRepeatability.RESET) and not identity.full_reset_sweep:
        exclusion += f"""
        AND NOT EXISTS (
            SELECT 1
            FROM auth_processing ap_history
            WHERE ap_history.corp_num = c.corp_num
              AND ap_history.flow_name = '{flow_sql}'
              AND ap_history.environment = '{env_sql}'
              AND ap_history.operation = '{operation_sql}'
              AND ap_history.operation_scope = '{scope_sql}'
              AND COALESCE(ap_history.dry_run, false) = false
        )
        """

    if identity.repeatability == AuthRepeatability.REPEATABLE:
        exclusion += f"""
        AND NOT EXISTS (
            SELECT 1
            FROM auth_processing ap_cycle
            WHERE ap_cycle.corp_num = c.corp_num
              AND ap_cycle.flow_name = '{flow_sql}'
              AND ap_cycle.environment = '{env_sql}'
              AND ap_cycle.operation = '{operation_sql}'
              AND ap_cycle.operation_scope = '{scope_sql}'
              AND ap_cycle.attempt_key = :auth_attempt_key
              AND COALESCE(ap_cycle.dry_run, false) = false
        )
        """

    return "", exclusion


def _auth_repeatable_real_history_priority_sql(
    *,
    flow_name: str,
    environment: str,
    identity: Optional[AuthProcessingIdentity],
) -> str:
    """Return ORDER BY expression that ranks never-run repeatable real corps first.

    Repeatable flows remain rerunnable across cycles: prior real history outside the current
    attempt_key is not excluded here, it only sorts after corps with no prior real attempt for
    the same flow/operation/scope identity.
    Dry-run history is ignored for real-run priority, and dry-runs do not apply this
    priority because they should not be treated as durable progress.
    """
    if (
        identity is None
        or identity.dry_run
        or identity.repeatability != AuthRepeatability.REPEATABLE
    ):
        return ""

    flow_sql = _escape_sql_literal(flow_name)
    env_sql = _escape_sql_literal(environment)
    operation_sql = _escape_sql_literal(identity.operation.value)
    scope_sql = _escape_sql_literal(identity.operation_scope.value)

    return f"""
        CASE
            WHEN EXISTS (
                SELECT 1
                FROM auth_processing ap_repeatable_history
                WHERE ap_repeatable_history.corp_num = c.corp_num
                  AND ap_repeatable_history.flow_name = '{flow_sql}'
                  AND ap_repeatable_history.environment = '{env_sql}'
                  AND ap_repeatable_history.operation = '{operation_sql}'
                  AND ap_repeatable_history.operation_scope = '{scope_sql}'
                  AND COALESCE(ap_repeatable_history.dry_run, false) = false
            ) THEN 1
            ELSE 0
        END
    """


def _order_by_sql(*terms: str) -> str:
    """Return an ORDER BY clause from non-empty terms."""
    cleaned = [term.strip() for term in terms if term and term.strip()]
    return f"ORDER BY\n            {', '.join(cleaned)}" if cleaned else ""



def _positive_int_csv(csv_val: str | None, *, name: str) -> Optional[str]:
    """Return safe positive integer CSV for SQL interpolation, or None when unset."""
    return positive_int_csv_for_sql(csv_val, name=name)


def _auth_migration_filter_ids(config) -> tuple[Optional[str], Optional[str]]:
    """Return Auth-only migration group/batch ID filters, without global fallback."""
    return auth_migration_filter_ids(config, require_any=True)


def _parse_corp_nums_csv(csv_val: str | None) -> List[str]:
    return parse_auth_corp_nums_csv(csv_val)


def _corp_nums_for_sql(values: Sequence[str] | str | None) -> List[str]:
    """Return normalized corp nums from settings-provided values."""
    if values is None:
        return []
    if isinstance(values, str):
        return parse_auth_corp_nums_csv(values)
    return parse_auth_corp_nums_csv(",".join(str(value) for value in values))


def _positive_int_sequence_for_sql(values: Sequence[int | str] | str | None, *, name: str) -> Optional[str]:
    """Return normalized positive integer CSV from settings-provided values."""
    if values is None:
        return None
    if isinstance(values, str):
        return positive_int_csv_for_sql(values, name=name)
    return positive_int_csv_for_sql(",".join(str(value) for value in values), name=name)


def get_auth_selected_corp_nums_query(
    config,
    selection_mode: AuthSelectionMode,
    *,
    auth_corp_nums: Sequence[str] | str | None | Any = _UNSET,
    auth_mig_group_ids: Sequence[int | str] | str | None | Any = _UNSET,
    auth_mig_batch_ids: Sequence[int | str] | str | None | Any = _UNSET,
) -> str:
    """Build SQL for the currently configured auth selection, returning one corp_num column.

    This cleanup/preview helper intentionally does not join auth_processing, does not apply
    reservation exclusions, and does not limit rows.
    """
    selection_mode = AuthSelectionMode(selection_mode)

    if selection_mode == AuthSelectionMode.MIGRATION_FILTER:
        if auth_mig_group_ids is _UNSET and auth_mig_batch_ids is _UNSET:
            mig_group_ids, mig_batch_ids = _auth_migration_filter_ids(config)
        else:
            mig_group_ids = _positive_int_sequence_for_sql(
                () if auth_mig_group_ids is _UNSET else auth_mig_group_ids,
                name='AUTH_MIG_GROUP_IDS',
            )
            mig_batch_ids = _positive_int_sequence_for_sql(
                () if auth_mig_batch_ids is _UNSET else auth_mig_batch_ids,
                name='AUTH_MIG_BATCH_IDS',
            )
            if not (mig_group_ids or mig_batch_ids):
                raise ValueError(
                    'AUTH_SELECTION_MODE=MIGRATION_FILTER requires AUTH_MIG_GROUP_IDS and/or AUTH_MIG_BATCH_IDS; '
                    'AUTH_CORP_NUMS only narrows the migration-filter cohort and does not replace '
                    'AUTH_MIG_GROUP_IDS/AUTH_MIG_BATCH_IDS; Auth flows do not fall back to global '
                    'MIG_GROUP_IDS/MIG_BATCH_IDS'
                )
        candidate_corp_nums = (
            _parse_corp_nums_csv(getattr(config, 'AUTH_CORP_NUMS', ''))
            if auth_corp_nums is _UNSET
            else _corp_nums_for_sql(auth_corp_nums)
        )
        mig_extra_where = ""
        if mig_batch_ids:
            mig_extra_where += f" AND b.id IN ({mig_batch_ids})"
        if mig_group_ids:
            mig_extra_where += f" AND g.id IN ({mig_group_ids})"
        if candidate_corp_nums:
            mig_extra_where += f" AND c.corp_num IN ({_quote_list(candidate_corp_nums)})"

        return f"""
        SELECT DISTINCT c.corp_num
        FROM mig_corp_batch mcb
        JOIN mig_batch b ON b.id = mcb.mig_batch_id
        JOIN mig_group g ON g.id = b.mig_group_id
        JOIN corporation c ON c.corp_num = mcb.corp_num
        JOIN corp_state cs
            ON cs.corp_num = c.corp_num
           AND cs.end_event_id IS NULL
        WHERE 1=1
        {mig_extra_where}
        AND c.corp_type_cd IN {CORP_TYPE_FILTER}
        """

    corp_nums = (
        _parse_corp_nums_csv(getattr(config, 'AUTH_CORP_NUMS', ''))
        if auth_corp_nums is _UNSET
        else _corp_nums_for_sql(auth_corp_nums)
    )
    corp_filter = f"AND c.corp_num IN ({_quote_list(corp_nums)})" if corp_nums else "AND 1=0"
    return f"""
    SELECT c.corp_num
    FROM corporation c
    JOIN corp_state cs
        ON cs.corp_num = c.corp_num
       AND cs.end_event_id IS NULL
    WHERE 1=1
      {corp_filter}
      AND c.corp_type_cd IN {CORP_TYPE_FILTER}
    """


def get_auth_reservable_corps_query(
    *,
    flow_name: str,
    config,
    batch_size: int,
    selection_mode: AuthSelectionMode,
    include_account_ids: bool = False,
    include_contact_email: bool = False,
    identity: Optional[AuthProcessingIdentity] = None,
) -> str:
    """
    Build SQL to select corps eligible to be reserved for an auth flow.

    Contract: Must SELECT at least:
        - corp_num
        - corp_type_cd
        - mig_batch_id

    Optionally selects:
        - account_ids (CSV string)
        - contact_email

    Identity-aware selection policy:
        - ONE_SHOT excludes existing non-dry-run rows by operation/scope.
        - REPEATABLE excludes active non-dry-run rows for the same corp/environment, but not historic rows.
        - RESET excludes existing non-dry-run reset rows by operation/scope.
        - Dry-runs ignore historical durable rows but still exclude active non-dry-run rows.

    Legacy callers that do not pass identity keep the prior anti-join by
    (corp_num, flow_name, environment).
    """
    selection_mode = AuthSelectionMode(selection_mode)

    environment = getattr(config, 'DATA_LOAD_ENV', '')
    mig_group_ids = None
    mig_batch_ids = None
    auth_corp_nums = []
    if selection_mode == AuthSelectionMode.MIGRATION_FILTER:
        mig_group_ids, mig_batch_ids = _auth_migration_filter_ids(config)
        auth_corp_nums = _parse_corp_nums_csv(getattr(config, 'AUTH_CORP_NUMS', ''))

    # Optional select columns
    account_map_cte = ""
    account_join = ""
    account_select = ""
    if include_account_ids:
        if selection_mode == AuthSelectionMode.MIGRATION_FILTER:
            # account_map is expensive; only include when requested.
            account_map_cte = f"""
            WITH account_map AS (
                SELECT mca.corp_num,
                       array_to_string(array_agg(DISTINCT mca.account_id ORDER BY mca.account_id), ',') AS account_ids
                FROM mig_corp_account mca
                JOIN mig_batch b2 ON b2.id = mca.mig_batch_id
                WHERE mca.target_environment = '{_escape_sql_literal(environment)}'
                {f" AND b2.id IN ({mig_batch_ids})" if mig_batch_ids else ""}
                {f" AND b2.mig_group_id IN ({mig_group_ids})" if mig_group_ids else ""}
                {f" AND mca.corp_num IN ({_quote_list(auth_corp_nums)})" if auth_corp_nums else ""}
                GROUP BY mca.corp_num
            )
            """
            account_join = "LEFT JOIN account_map am ON am.corp_num = c.corp_num"
            account_select = ", COALESCE(am.account_ids, NULL::varchar(100)) AS account_ids"
        else:
            # MANUAL
            account_select = ", NULL::varchar(100) AS account_ids"

    contact_select = ""
    if include_contact_email:
        if auth_custom_contact_email_override(config) is not None:
            contact_select = ", CAST(:auth_custom_contact_email AS varchar(254)) AS contact_email"
        else:
            contact_select = ", c.admin_email AS contact_email"

    ap_join, ap_exclusion_where = _auth_processing_exclusion_sql(
        flow_name=flow_name,
        environment=environment,
        identity=identity,
    )
    repeatable_priority_order = _auth_repeatable_real_history_priority_sql(
        flow_name=flow_name,
        environment=environment,
        identity=identity,
    )

    # MIG filters for MIGRATION_FILTER mode
    mig_extra_where = ""
    if selection_mode == AuthSelectionMode.MIGRATION_FILTER:
        if mig_batch_ids:
            mig_extra_where += f" AND b.id IN ({mig_batch_ids})"
        if mig_group_ids:
            mig_extra_where += f" AND g.id IN ({mig_group_ids})"
        if auth_corp_nums:
            mig_extra_where += f" AND c.corp_num IN ({_quote_list(auth_corp_nums)})"

    if selection_mode == AuthSelectionMode.MIGRATION_FILTER:
        order_by = _order_by_sql(
            f"{repeatable_priority_order} ASC" if repeatable_priority_order else "",
            "b.id ASC",
            "c.corp_num ASC",
        )
        query = f"""
        {account_map_cte}
        SELECT
            c.corp_num,
            c.corp_type_cd,
            b.id AS mig_batch_id
            {account_select}
            {contact_select}
        FROM mig_corp_batch mcb
        JOIN mig_batch b ON b.id = mcb.mig_batch_id
        JOIN mig_group g ON g.id = b.mig_group_id
        JOIN corporation c ON c.corp_num = mcb.corp_num
        JOIN corp_state cs
            ON cs.corp_num = c.corp_num
           AND cs.end_event_id IS NULL
        {account_join}
        {ap_join}
        WHERE 1=1
        {mig_extra_where}
        AND c.corp_type_cd IN {CORP_TYPE_FILTER}
        {ap_exclusion_where}
        {order_by}
        LIMIT {int(batch_size)}
        """
        return query

    # MANUAL
    corp_nums = _parse_corp_nums_csv(getattr(config, 'AUTH_CORP_NUMS', ''))
    corp_filter = f"AND c.corp_num IN ({_quote_list(corp_nums)})" if corp_nums else "AND 1=0"
    manual_input_order = (
        f"array_position(ARRAY[{_quote_list(corp_nums)}]::text[], c.corp_num::text) ASC"
        if corp_nums
        else ""
    )
    order_by = _order_by_sql(
        f"{repeatable_priority_order} ASC" if repeatable_priority_order else "",
        manual_input_order,
        "c.corp_num ASC",
    )

    query = f"""
    SELECT
        c.corp_num,
        c.corp_type_cd,
        NULL::integer AS mig_batch_id
        {account_select}
        {contact_select}
    FROM corporation c
    JOIN corp_state cs
        ON cs.corp_num = c.corp_num
       AND cs.end_event_id IS NULL
    {ap_join}
    WHERE 1=1
      {corp_filter}
      AND c.corp_type_cd IN {CORP_TYPE_FILTER}
      {ap_exclusion_where}
    {order_by}
    LIMIT {int(batch_size)}
    """
    return query


def get_auth_reservable_count_query(
    *,
    flow_name: str,
    config,
    selection_mode: AuthSelectionMode,
    identity: Optional[AuthProcessingIdentity] = None,
) -> str:
    """
    Count corps eligible to be reserved for this auth flow.

    Must match get_auth_reservable_corps_query(...) filters, including:
      - selection_mode logic
      - MIG filters (when enabled)
      - corp type filter
      - corp_state current row (end_event_id IS NULL)
      - identity-aware auth_processing exclusion policy, or legacy exclusion when identity is omitted
    """
    selection_mode = AuthSelectionMode(selection_mode)

    environment = getattr(config, 'DATA_LOAD_ENV', '')
    mig_group_ids = None
    mig_batch_ids = None
    auth_corp_nums = []
    if selection_mode == AuthSelectionMode.MIGRATION_FILTER:
        mig_group_ids, mig_batch_ids = _auth_migration_filter_ids(config)
        auth_corp_nums = _parse_corp_nums_csv(getattr(config, 'AUTH_CORP_NUMS', ''))

    ap_join, ap_exclusion_where = _auth_processing_exclusion_sql(
        flow_name=flow_name,
        environment=environment,
        identity=identity,
    )

    mig_extra_where = ""
    if selection_mode == AuthSelectionMode.MIGRATION_FILTER:
        if mig_batch_ids:
            mig_extra_where += f" AND b.id IN ({mig_batch_ids})"
        if mig_group_ids:
            mig_extra_where += f" AND g.id IN ({mig_group_ids})"
        if auth_corp_nums:
            mig_extra_where += f" AND c.corp_num IN ({_quote_list(auth_corp_nums)})"

    if selection_mode == AuthSelectionMode.MIGRATION_FILTER:
        return f"""
        SELECT count(*)
        FROM mig_corp_batch mcb
        JOIN mig_batch b ON b.id = mcb.mig_batch_id
        JOIN mig_group g ON g.id = b.mig_group_id
        JOIN corporation c ON c.corp_num = mcb.corp_num
        JOIN corp_state cs
            ON cs.corp_num = c.corp_num
           AND cs.end_event_id IS NULL
        {ap_join}
        WHERE 1=1
        {mig_extra_where}
        AND c.corp_type_cd IN {CORP_TYPE_FILTER}
        {ap_exclusion_where}
        """

    corp_nums = _parse_corp_nums_csv(getattr(config, 'AUTH_CORP_NUMS', ''))
    corp_filter = f"AND c.corp_num IN ({_quote_list(corp_nums)})" if corp_nums else "AND 1=0"
    return f"""
    SELECT count(*)
    FROM corporation c
    JOIN corp_state cs
        ON cs.corp_num = c.corp_num
       AND cs.end_event_id IS NULL
    {ap_join}
    WHERE 1=1
      {corp_filter}
      AND c.corp_type_cd IN {CORP_TYPE_FILTER}
      {ap_exclusion_where}
    """


def get_auth_business_profiles_query(corp_nums: List[str], suffix: str) -> str:
    """
    Batch-friendly business profile lookup for Auth API actions.

    Returns one row per corp_num with:
      - identifier (corp_num)
      - legal_name (current CO/NB corp_name + suffix)
      - legal_type (corp_type_cd)
      - admin_email (corporation.admin_email)
      - pass_code (corporation.corp_password)

    NOTE: Callers must never log or persist pass_code.
    """
    if not corp_nums:
        return """
        SELECT
            NULL::varchar(10)  AS identifier,
            NULL::varchar(150) AS legal_name,
            NULL::varchar(3)   AS legal_type,
            NULL::varchar(254) AS admin_email,
            NULL::varchar(300) AS pass_code
        WHERE 1=0;
        """

    corp_nums_up = [c.strip().upper() for c in corp_nums if c and c.strip()]
    corp_nums_sql = _quote_list(corp_nums_up)
    suffix_sql = _escape_sql_literal(suffix or "")

    return f"""
    SELECT DISTINCT ON (c.corp_num)
        c.corp_num AS identifier,
        (COALESCE(NULLIF(trim(cn.corp_name), ''), c.corp_num) || '{suffix_sql}') AS legal_name,
        c.corp_type_cd AS legal_type,
        c.admin_email AS admin_email,
        c.corp_password AS pass_code
    FROM corporation c
    LEFT JOIN corp_name cn
        ON cn.corp_num = c.corp_num
       AND cn.end_event_id IS NULL
       AND cn.corp_name_typ_cd IN ('CO', 'NB')
    WHERE c.corp_num IN ({corp_nums_sql})
    ORDER BY
        c.corp_num,
        CASE cn.corp_name_typ_cd WHEN 'CO' THEN 0 WHEN 'NB' THEN 1 ELSE 2 END,
        cn.start_event_id DESC NULLS LAST;
    """
