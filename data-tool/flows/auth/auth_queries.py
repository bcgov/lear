from __future__ import annotations

from typing import List, Sequence

from .auth_models import AuthSelectionMode

# Match the existing tombstone corp type cohort by default.
CORP_TYPE_FILTER = "('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')"


def _escape_sql_literal(val: str) -> str:
    """Escape a value for safe embedding in a SQL single-quoted literal."""
    return (val or "").replace("'", "''")


def _quote_list(values: Sequence[str]) -> str:
    """Quote/escape a list of values for SQL IN (...) lists."""
    return ", ".join([f"'{_escape_sql_literal(v)}'" for v in values])


def _parse_corp_nums_csv(csv_val: str | None) -> List[str]:
    if not csv_val:
        return []
    parts: List[str] = []
    for tok in str(csv_val).split(','):
        t = tok.strip().upper()
        if t:
            parts.append(t)
    # Deduplicate while preserving order
    seen = set()
    out: List[str] = []
    for t in parts:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def get_auth_reservable_corps_query(
    *,
    flow_name: str,
    config,
    batch_size: int,
    selection_mode: AuthSelectionMode,
    include_account_ids: bool = False,
    include_contact_email: bool = False,
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

    IMPORTANT: Always excludes corps already present in auth_processing for the same
    (corp_num, flow_name, environment).
    """
    environment = getattr(config, 'DATA_LOAD_ENV', '')
    mig_group_ids = getattr(config, 'MIG_GROUP_IDS', None)
    mig_batch_ids = getattr(config, 'MIG_BATCH_IDS', None)
    source_flow = getattr(config, 'AUTH_SOURCE_FLOW_NAME', 'tombstone-flow')

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
                GROUP BY mca.corp_num
            )
            """
            account_join = "LEFT JOIN account_map am ON am.corp_num = c.corp_num"
            account_select = ", COALESCE(am.account_ids, NULL::varchar(100)) AS account_ids"
        elif selection_mode == AuthSelectionMode.CORP_PROCESSING:
            account_select = ", cp.account_ids AS account_ids"
        else:
            # MANUAL
            account_select = ", NULL::varchar(100) AS account_ids"

    contact_select = ", c.admin_email AS contact_email" if include_contact_email else ""

    ap_join = f"""
    LEFT JOIN auth_processing ap
        ON ap.corp_num = c.corp_num
       AND ap.flow_name = '{_escape_sql_literal(flow_name)}'
       AND ap.environment = '{_escape_sql_literal(environment)}'
    """

    # MIG filters for MIGRATION_FILTER mode
    mig_extra_where = ""
    if selection_mode == AuthSelectionMode.MIGRATION_FILTER:
        if mig_batch_ids:
            mig_extra_where += f" AND b.id IN ({mig_batch_ids})"
        if mig_group_ids:
            mig_extra_where += f" AND g.id IN ({mig_group_ids})"

    if selection_mode == AuthSelectionMode.MIGRATION_FILTER:
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
        AND ap.corp_num IS NULL
        LIMIT {int(batch_size)}
        """
        return query

    if selection_mode == AuthSelectionMode.CORP_PROCESSING:
        query = f"""
        SELECT
            cp.corp_num,
            c.corp_type_cd,
            cp.mig_batch_id AS mig_batch_id
            {account_select}
            {contact_select}
        FROM corp_processing cp
        JOIN corporation c ON c.corp_num = cp.corp_num
        JOIN corp_state cs
            ON cs.corp_num = c.corp_num
           AND cs.end_event_id IS NULL
        {ap_join}
        WHERE 1=1
          AND cp.flow_name = '{_escape_sql_literal(source_flow)}'
          AND cp.environment = '{_escape_sql_literal(environment)}'
          AND cp.processed_status IN ('COMPLETED', 'PARTIAL')
          AND c.corp_type_cd IN {CORP_TYPE_FILTER}
          AND ap.corp_num IS NULL
        LIMIT {int(batch_size)}
        """
        return query

    # MANUAL
    corp_nums = _parse_corp_nums_csv(getattr(config, 'AUTH_CORP_NUMS', ''))
    corp_filter = f"AND c.corp_num IN ({_quote_list(corp_nums)})" if corp_nums else "AND 1=0"

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
      AND ap.corp_num IS NULL
    LIMIT {int(batch_size)}
    """
    return query


def get_auth_reservable_count_query(
    *,
    flow_name: str,
    config,
    selection_mode: AuthSelectionMode,
) -> str:
    """
    Count corps eligible to be reserved for this auth flow.

    Must match get_auth_reservable_corps_query(...) filters, including:
      - selection_mode logic
      - MIG filters (when enabled)
      - corp type filter
      - corp_state current row (end_event_id IS NULL)
      - exclusion of existing auth_processing rows for (corp_num, flow_name, environment)
    """
    environment = getattr(config, 'DATA_LOAD_ENV', '')
    mig_group_ids = getattr(config, 'MIG_GROUP_IDS', None)
    mig_batch_ids = getattr(config, 'MIG_BATCH_IDS', None)
    source_flow = getattr(config, 'AUTH_SOURCE_FLOW_NAME', 'tombstone-flow')

    ap_join = f"""
    LEFT JOIN auth_processing ap
        ON ap.corp_num = c.corp_num
       AND ap.flow_name = '{_escape_sql_literal(flow_name)}'
       AND ap.environment = '{_escape_sql_literal(environment)}'
    """

    mig_extra_where = ""
    if selection_mode == AuthSelectionMode.MIGRATION_FILTER:
        if mig_batch_ids:
            mig_extra_where += f" AND b.id IN ({mig_batch_ids})"
        if mig_group_ids:
            mig_extra_where += f" AND g.id IN ({mig_group_ids})"

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
        AND ap.corp_num IS NULL
        """

    if selection_mode == AuthSelectionMode.CORP_PROCESSING:
        return f"""
        SELECT count(*)
        FROM corp_processing cp
        JOIN corporation c ON c.corp_num = cp.corp_num
        JOIN corp_state cs
            ON cs.corp_num = c.corp_num
           AND cs.end_event_id IS NULL
        {ap_join}
        WHERE 1=1
          AND cp.flow_name = '{_escape_sql_literal(source_flow)}'
          AND cp.environment = '{_escape_sql_literal(environment)}'
          AND cp.processed_status IN ('COMPLETED', 'PARTIAL')
          AND c.corp_type_cd IN {CORP_TYPE_FILTER}
          AND ap.corp_num IS NULL
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
      AND ap.corp_num IS NULL
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
