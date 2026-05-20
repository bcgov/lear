import pandas as pd
from typing import Dict, Iterable, List, Sequence
import re

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

def get_saf_criteria_query(updated_corp_nums: list) -> str:
    return """
    SELECT corp_num FROM mv_legacy_corps_data
    where 1 = 1
    and is_active = true
    and is_frozen = false
    and in_dissolution = false
    and migrated <> 'Y'
    and has_password = true
    and has_officers = false
    and meets_main_criteria = true
    and has_3rd_party = false
    and admin_email is not null
    and email_used_count = 1
    and director_count = 1
    and address_all_any_bad_count = 0
    and meets_share_criteria = true
    and has_bar_filing = false
    and directors_within_bc = true
    and is_bad_email = false
    and corp_num in {updated_corp_nums}
"""

def get_criteria_query(criteria: str) -> str:
    key = (criteria or '').strip().upper()
    if key == 'SAF':
        return get_saf_criteria_query()
    raise ValueError(f'unsupported criteria: {criteria}')