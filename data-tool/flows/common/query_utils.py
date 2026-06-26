import pandas as pd
from typing import Dict, Iterable, List, Sequence
import re

from sqlalchemy import Engine
from common.colin_utils import colin_oracle_corp_num_list_format

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

def get_candidates_not_matching_saf_criteria_query(updated_corp_nums: list) -> str:
    in_list = colin_oracle_corp_num_list_format(updated_corp_nums)
    return f"""
    SELECT corp_num FROM mv_legacy_corps_data
    WHERE 1 = 1
    AND corp_num IN {in_list}
    AND corp_num NOT IN (
    SELECT corp_num FROM mv_legacy_corps_data
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

def get_fallout_corp_nums(criteria: str, updated_corp_nums: list) -> str:
    key = (criteria or '').strip().upper()
    if key == 'SAF':
        return get_candidates_not_matching_saf_criteria_query(updated_corp_nums)
    raise ValueError(f'unsupported criteria: {criteria}')

def prune_candidates_from_cp(pruning_corps_list: list) -> str:
    in_list = colin_oracle_corp_num_list_format(pruning_corps_list)
    return f"""
    DELETE FROM corp_processing
    WHERE corp_num IN {in_list}
    """

def prune_candidates_from_batch(pruning_corps_list: list) -> str:
    in_list = colin_oracle_corp_num_list_format(pruning_corps_list)
    return f"""
    DELETE FROM mig_corp_batch
    WHERE corp_num IN {in_list}
    """

def prune_candidates_from_account(pruning_corps_list: list) -> str:
    in_list = colin_oracle_corp_num_list_format(pruning_corps_list)
    return f"""
    DELETE FROM mig_corp_account
    WHERE corp_num IN {in_list}
    """

def get_cutoff_timestamp_query() -> str:
    return f"""
    SELECT extracted_at FROM colin_extract_version
    """
