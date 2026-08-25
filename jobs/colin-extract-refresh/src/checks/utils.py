
from math import ceil
import os
import re
from typing import List, Literal

import oracledb
import pandas as pd
from sqlalchemy import create_engine, text

def colin_oracle_init(config) -> None:
    try:
        lib_dir = os.environ.get("ORACLE_CLIENT_LIB_DIR", "")
        oracledb.init_oracle_client(lib_dir=lib_dir)
        print('👷 Enable thick mode:', not oracledb.is_thin_mode())
        print('👷 Instant Client version:', oracledb.clientversion())
        engine = create_engine(config.SQLALCHEMY_DATABASE_URI_COLIN_ORACLE)
            # Check oracle connection
        with engine.connect() as conn:
                    res = conn.execute(
                        text("""SELECT SYS_CONTEXT('USERENV', 'DB_NAME') FROM DUAL""")
                    ).scalar()
                    if not res:
                        raise ValueError("Failed to retrieve the current database name.")
                    print(f'✅ Connected to Oracle database: {res}')
        return engine
    except Exception as e:
        raise Exception('Failed to create engine for COLIN Oracle DB') from e

def build_corp_list(corp_list: str, chunksize: int) -> str:
    if not str(corp_list).strip():
        raise ValueError('empty corp_list')
    corp_nums = re.findall(r"'([^']*)'", corp_list)
    batch_size = min(chunksize, 999)
    num_batches = ceil(len(corp_nums) / batch_size)

    batch_ctes: list[str] = []
    batch_names: list[str] = []
    for idx in range(num_batches):
        batch = corp_nums[idx * batch_size: (idx +1)* batch_size]
        name = f'corp_list_{idx+1}'
        batch_names.append(name)
        args_sql = ",".join("'" + x.replace("'", "''") + "'" for x in batch)
        batch_ctes.append(
            f'{name} AS (SELECT column_value AS corp_num FROM TABLE(sys.odcivarchar2list({args_sql})))'
        )

    union_lines = [f' SELECT corp_num FROM {batch_names[0]}']
    union_lines.extend(f' UNION ALL SELECT corp_num FROM {name}' for name in batch_names[1:])
    corp_list_cte = 'corp_list AS (\n'+ '\n'.join(union_lines) + '\n)'
    return ',\n'.join([*batch_ctes, corp_list_cte])

def get_updated_identifiers(timestamp: str, corp_list: str, chunk_size: int, scope: Literal['batch', 'full']) -> str:
    corp_list_ctes = 'WITH '
    frozen_ctes = ''
    join_ctes = 'corporation'
    if scope == 'batch':
        join_ctes = 'corp_list'
        if not str(corp_list).strip():
            raise ValueError('empty corp_list')
        corp_list_ctes += build_corp_list(corp_list, chunk_size) + ',\n'
    if scope == 'full':
        frozen_ctes = frozen_cte() 
    query = f"""
    {corp_list_ctes}
    latest_event AS (
        SELECT e.event_id,
                e.corp_num,
                e.event_typ_cd,
                e.event_timestmp,
                e.trigger_dts,
                ROW_NUMBER() OVER (
                PARTITION BY e.corp_num
                ORDER BY e.event_timestmp DESC, e.event_id DESC
                ) AS rn
        FROM event e
        JOIN {join_ctes} c
            ON c.corp_num = e.corp_num
        WHERE e.event_timestmp > TIMESTAMP '{timestamp}' - INTERVAL '2' HOUR
        {frozen_ctes}
    ) SELECT le.EVENT_ID,
        le.corp_num,
        le.event_typ_cd,
        le.event_timestmp,
        le.trigger_dts,
        f.FILING_TYP_CD
    FROM latest_event le
    LEFT JOIN filing f on le.EVENT_ID = f.EVENT_ID
    WHERE rn = 1
    ORDER BY le.event_timestmp DESC, le.EVENT_ID DESC
    """
    return query

def get_identifiers_per_batch(mig_batch_id: int, target_schema: str) -> str:
    return f"""
    SELECT string_agg(pg_catalog.quote_literal(trim(CAST(mcb.corp_num AS text))), ',') AS corp_list
    FROM {target_schema}.mig_corp_batch mcb
    WHERE mcb.mig_batch_id IN ({mig_batch_id})
    """

def unfreeze_identifiers(target_schema: str) -> str:
    return f"""
    UPDATE {target_schema}.corporation AS c
    SET corp_frozen_type_cd = NULL
    FROM {target_schema}.mig_group AS mg
            JOIN {target_schema}.mig_batch AS mb ON mb.mig_group_id = mg.id
            JOIN {target_schema}.mig_corp_batch AS mcb ON mcb.mig_batch_id = mb.id
    WHERE c.corp_num = mcb.corp_num
    -- cprd
    and mg.name in ('group_0', 'group_1', 'group_3', 'group_4','gcp_migration_group_test','misc_group')
    and mg.source_db = 'cprd'
    and mg.target_environment = 'prod'
    AND c.corp_frozen_type_cd IS NOT NULL;
    """

def frozen_cte() -> str:
    return f"""
    AND NOT (
            EXISTS (
            SELECT 1
            FROM corporation c2
                WHERE c2.corp_num = e.corp_num
                AND c2.corp_frozen_typ_cd = 'C'
            )
            AND EXISTS (
            SELECT 1
            FROM corp_early_adopters cea
            WHERE cea.corp_num = e.corp_num
            )
        )
    """

def get_updated_identifiers_for_batch(timestamp: str, corp_list: str, chunk_size: int, scope: str) -> str:
    """per batch get identifiers"""
    return get_updated_identifiers(timestamp, corp_list, chunk_size, scope)


BC_PREFIX_RE = re.compile(r"^BC(\d+)$", re.IGNORECASE)

def convert_result_set_to_dict(rs):
    df = pd.DataFrame(rs, columns=rs.keys())
    result_dict = df.to_dict('records')
    return result_dict

def corpnum_to_oracle_ids(target_ids: str | bytes | tuple | list | None) -> List[str]:
    """
    Convert TARGET/Postgres corp ids into Oracle corporation.corp_num values.

    For ids like BC0460007 -> 0460007
    Otherwise leave as-is (A1234567 -> A1234567)

    De-dupe while preserving order (avoid wasting Oracle IN-list slots).
    """
    if target_ids is None:
        return None
    
    if isinstance(target_ids, (tuple, list)) and len(target_ids) == 1:
        target_ids = target_ids[0]
    
    if isinstance(target_ids, bytes):
        target_ids = target_ids.decode()
    
    raw = str(target_ids).strip()
    if not raw:
        return None
    parsed = re.findall(r"'((?:''|[^'])*)'", raw)
    if not parsed:
        return None
    target_ids = [p.strip() for p in parsed if p.strip()]

    out: List[str] = []
    seen: set[str] = set()

    for target_id in target_ids:
        m = BC_PREFIX_RE.match(target_id)
        oracle_id = m.group(1) if m else target_id

        if oracle_id not in seen:
            out.append(oracle_id)
            seen.add(oracle_id)

    if not out:
        return None
    return ",".join("'" + x.replace("'", "''") + "'" for x in out)
def colin_oracle_corp_num_list_format(corp_nums: list[str]) -> str:
    def q(s: str) -> str:
        return "'" + str(s).replace("'","''") + "'"
    return '(' + ','.join(q(c) for c in corp_nums) + ')'

def get_candidates_not_matching_saf_criteria_query(updated_corp_nums: list, target_schema: str) -> str:
    in_list = colin_oracle_corp_num_list_format(updated_corp_nums)
    return f"""
    SELECT corp_num FROM {target_schema}.mv_legacy_corps_data
    WHERE 1 = 1
    AND corp_num IN {in_list}
    AND corp_num NOT IN (
    SELECT corp_num FROM {target_schema}.mv_legacy_corps_data
    WHERE 1 = 1
    AND is_active = true
    AND is_frozen = false
    AND in_dissolution = false
    AND migrated <> 'Y'
    AND has_password = true
    AND meets_main_criteria = true
    AND has_3rd_party = false
    AND admin_email IS NOT NULL
    AND email_used_count = 1
    AND director_count = 1
    AND address_all_any_bad_count = 0
    AND meets_share_criteria = true
    AND has_bar_filing = false
    AND directors_within_bc = true
    AND is_bad_email = false
    AND is_email_excluded = false
    AND is_migration_excluded = false
    )
"""

def get_fallout_corp_nums(criteria: str, updated_corp_nums: list, target_schema: str) -> str:
    key = (criteria or '').strip().upper()
    if key == 'SAF':
        return get_candidates_not_matching_saf_criteria_query(updated_corp_nums, target_schema)
    raise ValueError(f'unsupported criteria: {criteria}')

def prune_candidates_from_cp(pruning_corps_list: list, target_schema: str) -> str:
    in_list = colin_oracle_corp_num_list_format(pruning_corps_list)
    return f"""
    DELETE FROM {target_schema}.corp_processing
    WHERE corp_num IN {in_list}
    """

def prune_candidates_from_batch(pruning_corps_list: list, target_schema: str) -> str:
    in_list = colin_oracle_corp_num_list_format(pruning_corps_list)
    return f"""
    DELETE FROM {target_schema}.mig_corp_batch
    WHERE corp_num IN {in_list}
    """

def prune_candidates_from_account(pruning_corps_list: list, target_schema: str) -> str:
    in_list = colin_oracle_corp_num_list_format(pruning_corps_list)
    return f"""
    DELETE FROM {target_schema}.mig_corp_account
    WHERE corp_num IN {in_list}
    """

def get_cutoff_timestamp_query(target_schema: str) -> str:
    return f"""
    SELECT extracted_at FROM {target_schema}.colin_extract_version
    """
