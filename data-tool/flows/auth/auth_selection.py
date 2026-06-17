from __future__ import annotations

import hashlib
from typing import List, Optional, Sequence


def parse_auth_corp_nums_csv(csv_val: str | None) -> List[str]:
    """Parse AUTH_CORP_NUMS permissively: trim, uppercase, drop blanks, dedupe in input order."""
    if not csv_val:
        return []

    parts: List[str] = []
    for tok in str(csv_val).split(','):
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


def canonical_auth_corp_nums_for_scope(csv_val: str | None) -> List[str]:
    """Return parsed AUTH_CORP_NUMS sorted for order-insensitive campaign identity."""
    return sorted(parse_auth_corp_nums_csv(csv_val))


def corp_nums_scope_hash(corp_nums: Sequence[str]) -> str:
    """Hash a canonical corp-num sequence for compact campaign scope identity."""
    return hashlib.sha256(','.join(corp_nums).encode('utf-8')).hexdigest()


def corp_nums_subset_scope(csv_val: str | None, *, all_label: str = 'ALL') -> str:
    """Return subset=... value for campaign/logging from AUTH_CORP_NUMS."""
    corp_nums = canonical_auth_corp_nums_for_scope(csv_val)
    if not corp_nums:
        return all_label
    return f"count={len(corp_nums)};sha256={corp_nums_scope_hash(corp_nums)}"


def parse_positive_int_csv(csv_val: str | None, *, name: str) -> List[str]:
    """Return normalized positive integer tokens, deduped in input order."""
    if csv_val is None:
        return []

    csv_text = str(csv_val).strip()
    if not csv_text:
        return []

    values: List[str] = []
    seen = set()
    for tok in csv_text.split(','):
        t = tok.strip()
        if not t:
            continue
        if not t.isdigit():
            raise ValueError(f'{name} must be a CSV of positive integers: {csv_val}')
        val = int(t)
        if val <= 0:
            raise ValueError(f'{name} must contain only positive integers: {csv_val}')
        normalized = str(val)
        if normalized not in seen:
            seen.add(normalized)
            values.append(normalized)
    return values


def positive_int_csv_for_sql(csv_val: str | None, *, name: str) -> Optional[str]:
    """Return normalized positive integer CSV for SQL interpolation, or None when unset."""
    values = parse_positive_int_csv(csv_val, name=name)
    return ', '.join(values) if values else None


def positive_int_csv_for_scope(csv_val: str | None, *, name: str) -> str:
    """Return normalized positive integer CSV for campaign scope, or ALL when unset."""
    values = parse_positive_int_csv(csv_val, name=name)
    return ','.join(values) if values else 'ALL'


def auth_migration_filter_ids(config, *, require_any: bool = False) -> tuple[Optional[str], Optional[str]]:
    """Return Auth-only migration group/batch ID SQL filters, without global fallback."""
    mig_group_ids = positive_int_csv_for_sql(
        getattr(config, 'AUTH_MIG_GROUP_IDS', None),
        name='AUTH_MIG_GROUP_IDS',
    )
    mig_batch_ids = positive_int_csv_for_sql(
        getattr(config, 'AUTH_MIG_BATCH_IDS', None),
        name='AUTH_MIG_BATCH_IDS',
    )
    if require_any and not (mig_group_ids or mig_batch_ids):
        raise ValueError(
            'AUTH_SELECTION_MODE=MIGRATION_FILTER requires AUTH_MIG_GROUP_IDS and/or AUTH_MIG_BATCH_IDS; '
            'AUTH_CORP_NUMS only narrows the migration-filter cohort and does not replace '
            'AUTH_MIG_GROUP_IDS/AUTH_MIG_BATCH_IDS; Auth flows do not fall back to global '
            'MIG_GROUP_IDS/MIG_BATCH_IDS'
        )
    return mig_group_ids, mig_batch_ids
