import pandas as pd
from typing import Dict, Iterable, List, Sequence
import re

BC_PREFIX_RE = re.compile(r"^BC(\d+)$", re.IGNORECASE)

def convert_result_set_to_dict(rs):
    df = pd.DataFrame(rs, columns=rs.keys())
    result_dict = df.to_dict('records')
    return result_dict

def corpnum_to_oracle_ids(target_ids: Sequence[str]) -> List[str]:
    """
    Convert TARGET/Postgres corp ids into Oracle corporation.corp_num values.

    For ids like BC0460007 -> 0460007
    Otherwise leave as-is (A1234567 -> A1234567)

    De-dupe while preserving order (avoid wasting Oracle IN-list slots).
    """
    out: List[str] = []
    seen: set[str] = set()

    for target_id in target_ids:
        m = BC_PREFIX_RE.match(target_id)
        oracle_id = m.group(1) if m else target_id

        if oracle_id not in seen:
            out.append(oracle_id)
            seen.add(oracle_id)

    return out