"""
Prerequisites:
  1. VPN connected (to reach COLIN Oracle).
  2. Cloud SQL Proxy running (pointing to GCP dev Business DB).
  3. Run prefect server (make run-prefect-server) and connected to prefect db.
  3. Environment variables configured in .env:
     - DATABASE_*_COLIN_ORACLE (Oracle host, user, password, service name)
     - DATABASE_* (LEAR Business DB host, user, password, db name)
     - VERIFY_LEGAL_TYPE (e.g., 'RLY' - the entity type to verify)
     - VERIFY_MIGRATION_OUTPUT (Optional: custom path for CSV report, defaults to /tmp/migration_verification_report.csv)
     - CORP_NAME_SUFFIX (Optional: suffix appended to legal names in LEAR during migration)
"""

import csv
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from prefect import flow, task
from prefect.cache_policies import NO_CACHE
from sqlalchemy import Engine, text

from common.init_utils import colin_oracle_init, get_config, lear_init


# Load config vars
VERIFY_LEGAL_TYPE = os.getenv('VERIFY_LEGAL_TYPE', 'RLY')
OUTPUT_CSV_PATH = os.getenv('VERIFY_MIGRATION_OUTPUT', '/tmp/migration_verification_report.csv')
CORP_NAME_SUFFIX = os.getenv('CORP_NAME_SUFFIX', ' - LVE_RLY_IMPORT_TEST')

# Mappings
FILING_TYPE_MAP = {
    'OTINC': 'incorporationApplication',
    'OTAMA': 'amalgamationApplication',
    'OTANN': 'annualReport',
    'OTADD': 'changeOfAddress',
    'OTCDR': 'changeOfDirectors',
    'OTVDS': 'dissolution',
    'OTDIS': 'dissolution',
    'OTSPE': 'specialResolution',
    'OTRES': 'restorationApplication',
    'OTNCN': 'changeOfName',
}
ROLE_MAP = {
    'DIR': 'director',
    'OFF': 'officer',
    'RCC': 'custodian',
    'RCM': 'receiver',
    'LIQ': 'liquidator',
}
STATE_MAP = {
    'ACT': 'ACTIVE',
    'HIS': 'HISTORICAL',
    'HDV': 'HISTORICAL'
}


class VerificationResult:
    def __init__(self, corp_num: str, table: str, field: str,
                 colin_value: str, lear_value: str, status: str, notes: str = ''):
        self.corp_num = corp_num
        self.table = table
        self.field = field
        self.colin_value = str(colin_value)[:200] if colin_value is not None else 'NULL'
        self.lear_value = str(lear_value)[:200] if lear_value is not None else 'NULL'
        self.status = status  # MATCH, MISMATCH, MISSING_IN_LEAR, MISSING_IN_COLIN, EXPECTED_GAP
        self.notes = notes

    def to_dict(self):
        return {
            'corp_num': self.corp_num,
            'table': self.table,
            'field': self.field,
            'colin_value': self.colin_value,
            'lear_value': self.lear_value,
            'status': self.status,
            'notes': self.notes,
        }


# --- Oracle Queries ---

def get_colin_businesses(engine: Engine, legal_type: str) -> List[dict]:
    query = f"""
        SELECT c.corp_num, c.corp_typ_cd, c.recognition_dts,
               (SELECT cn.corp_nme FROM corp_name cn
                WHERE cn.corp_num = c.corp_num
                  AND cn.end_event_id IS NULL
                  AND cn.corp_name_typ_cd IN ('CO', 'NB')
                  AND ROWNUM = 1) AS legal_name,
               (SELECT cs.state_typ_cd FROM corp_state cs
                WHERE cs.corp_num = c.corp_num
                  AND cs.end_event_id IS NULL
                  AND ROWNUM = 1) AS state_typ_cd
        FROM corporation c
        WHERE c.corp_typ_cd = '{legal_type}'
        ORDER BY c.corp_num
    """
    with engine.connect() as conn:
        result = conn.execute(text(query))
        return [{'corp_num': r[0], 'corp_typ_cd': r[1], 'recognition_dts': r[2],
                 'legal_name': (r[3] or '').strip() if r[3] else '',
                 'state_typ_cd': r[4]} for r in result.fetchall()]


def get_colin_filings(engine: Engine, corp_nums: List[str]) -> Dict[str, List[dict]]:
    if not corp_nums:
        return {}
    results = defaultdict(list)
    chunk_size = 900
    for i in range(0, len(corp_nums), chunk_size):
        chunk = corp_nums[i:i + chunk_size]
        placeholders = ','.join([f"'{c}'" for c in chunk])
        query = f"""
            SELECT e.corp_num, e.event_id, f.filing_typ_cd, f.effective_dt, trim(f.ods_typ_cd) as ods_type_cd
            FROM event e
            LEFT JOIN filing f ON f.event_id = e.event_id
            WHERE e.corp_num IN ({placeholders})
              AND e.event_typ_cd NOT IN ('BNUPD', 'ADDLEDGR')
            ORDER BY e.corp_num, e.event_id
        """
        with engine.connect() as conn:
            result = conn.execute(text(query))
            for r in result.fetchall():
                results[r[0]].append({
                    'event_id': str(r[1]),
                    'filing_typ_cd': r[2],
                    'effective_dt': r[3],
                    'ods_type_cd': r[4],
                })
    return dict(results)


def get_colin_parties(engine: Engine, corp_nums: List[str]) -> Dict[str, List[dict]]:
    if not corp_nums:
        return {}
    results = defaultdict(list)
    chunk_size = 900
    for i in range(0, len(corp_nums), chunk_size):
        chunk = corp_nums[i:i + chunk_size]
        placeholders = ','.join([f"'{c}'" for c in chunk])
        query = f"""
            SELECT p.corp_num, p.corp_party_id, p.first_nme, p.last_nme,
                   p.party_typ_cd, p.mailing_addr_id, p.delivery_addr_id,
                   p.appointment_dt, p.cessation_dt
            FROM corp_party p
            WHERE p.corp_num IN ({placeholders})
              AND (
                (p.end_event_id IS NULL)
                OR (
                  p.end_event_id IS NOT NULL
                  AND NOT EXISTS (
                    SELECT 1 FROM corp_party p2
                    WHERE p2.corp_num = p.corp_num
                      AND p2.party_typ_cd = p.party_typ_cd
                      AND p2.start_event_id > p.end_event_id
                      AND p2.end_event_id IS NULL
                  )
                )
              )
            ORDER BY p.corp_num, p.corp_party_id
        """
        with engine.connect() as conn:
            result = conn.execute(text(query))
            for r in result.fetchall():
                results[r[0]].append({
                    'corp_party_id': str(r[1]),
                    'first_nme': (r[2] or '').strip().upper() if r[2] else '',
                    'last_nme': (r[3] or '').strip().upper() if r[3] else '',
                    'party_typ_cd': r[4],
                    'mailing_addr_id': str(r[5]) if r[5] else None,
                    'delivery_addr_id': str(r[6]) if r[6] else None,
                    'appointment_dt': str(r[7])[:10] if r[7] else None,
                    'cessation_dt': str(r[8])[:10] if r[8] else None,
                })
    return dict(results)


def get_colin_addresses(engine: Engine, corp_nums: List[str]) -> Dict[Tuple[str, str], dict]:
    if not corp_nums:
        return {}
    results = {}
    chunk_size = 900
    
    for i in range(0, len(corp_nums), chunk_size):
        chunk = corp_nums[i:i + chunk_size]
        placeholders = ','.join([f"'{c}'" for c in chunk])
        query = f"""
            SELECT a.addr_id, a.addr_line_1, a.city, a.postal_cd, a.province,
                   p.corp_num, p.mailing_addr_id, p.delivery_addr_id
            FROM corp_party p
            JOIN address a ON a.addr_id = p.mailing_addr_id OR a.addr_id = p.delivery_addr_id
            WHERE p.corp_num IN ({placeholders})
              AND p.end_event_id IS NULL
        """
        with engine.connect() as conn:
            result = conn.execute(text(query))
            for r in result.fetchall():
                addr_id = str(r[0])
                corp_num = r[5]
                addr_type = 'unknown'
                if str(r[6]) == addr_id:
                    addr_type = 'mailing'
                elif str(r[7]) == addr_id:
                    addr_type = 'delivery'
                results[(corp_num, addr_id)] = {
                    'street': (r[1] or '').strip().upper() if r[1] else '',
                    'city': (r[2] or '').strip().upper() if r[2] else '',
                    'postal_cd': (r[3] or '').strip().upper().replace(' ', '') if r[3] else '',
                    'address_type': addr_type,
                }
    return results


def get_colin_offices(engine: Engine, corp_nums: List[str]) -> Dict[str, List[dict]]:
    if not corp_nums:
        return {}
    results = defaultdict(list)
    chunk_size = 900
    for i in range(0, len(corp_nums), chunk_size):
        chunk = corp_nums[i:i + chunk_size]
        placeholders = ','.join([f"'{c}'" for c in chunk])
        query = f"""
            SELECT o.corp_num, o.office_typ_cd, o.start_event_id, o.end_event_id
            FROM office o
            WHERE o.corp_num IN ({placeholders})
        """
        with engine.connect() as conn:
            result = conn.execute(text(query))
            for r in result.fetchall():
                results[r[0]].append({
                    'office_typ_cd': r[1],
                    'start_event_id': str(r[2]),
                    'end_event_id': str(r[3]) if r[3] else None,
                })
    return dict(results)


def get_colin_aliases(engine: Engine, corp_nums: List[str]) -> Dict[str, List[dict]]:
    """Fetch aliases (DBA names) from COLIN where corp_name_typ_cd = 'TR'."""
    if not corp_nums:
        return {}
    results = defaultdict(list)
    chunk_size = 900
    for i in range(0, len(corp_nums), chunk_size):
        chunk = corp_nums[i:i + chunk_size]
        placeholders = ','.join([f"'{c}'" for c in chunk])
        query = f"""
            SELECT cn.corp_num, cn.corp_nme
            FROM corp_name cn
            WHERE cn.corp_num IN ({placeholders})
              AND cn.end_event_id IS NULL
              AND cn.corp_name_typ_cd = 'TR'
        """
        with engine.connect() as conn:
            result = conn.execute(text(query))
            for r in result.fetchall():
                results[r[0]].append({
                    'alias': (r[1] or '').strip().upper() if r[1] else '',
                })
    return dict(results)


def get_colin_comments(engine: Engine, corp_nums: List[str]) -> Dict[str, List[dict]]:
    """Fetch business comments from COLIN."""
    if not corp_nums:
        return {}
    results = defaultdict(list)
    chunk_size = 900
    for i in range(0, len(corp_nums), chunk_size):
        chunk = corp_nums[i:i + chunk_size]
        placeholders = ','.join([f"'{c}'" for c in chunk])
        query = f"""
            SELECT cc.corp_num, cc.comments
            FROM corp_comments cc
            WHERE cc.corp_num IN ({placeholders})
        """
        with engine.connect() as conn:
            result = conn.execute(text(query))
            for r in result.fetchall():
                comment_text = (r[1] or '').strip().upper() if r[1] else ''
                if comment_text:
                    results[r[0]].append({
                        'comment': comment_text,
                    })
    return dict(results)


def get_colin_filing_comments(engine: Engine, corp_nums: List[str]) -> Dict[str, List[dict]]:
    """Fetch filing-level comments (ledger notations) from COLIN."""
    if not corp_nums:
        return {}
    results = defaultdict(list)
    chunk_size = 900
    for i in range(0, len(corp_nums), chunk_size):
        chunk = corp_nums[i:i + chunk_size]
        placeholders = ','.join([f"'{c}'" for c in chunk])
        query = f"""
            SELECT e.corp_num, trim(lt.notation) AS comment_text
            FROM ledger_text lt
            JOIN event e ON e.event_id = lt.event_id
            WHERE e.corp_num IN ({placeholders})
              AND nullif(trim(lt.notation), '') IS NOT NULL
            UNION ALL
            SELECT e.corp_num, trim(cl.ledger_desc) AS comment_text
            FROM conv_ledger cl
            JOIN event e ON e.event_id = cl.event_id
            WHERE e.corp_num IN ({placeholders})
              AND nullif(trim(cl.ledger_desc), '') IS NOT NULL
        """
        with engine.connect() as conn:
            result = conn.execute(text(query))
            for r in result.fetchall():
                comment_text = (r[1] or '').strip().upper() if r[1] else ''
                if comment_text:
                    results[r[0]].append({
                        'comment': comment_text,
                    })
    return dict(results)


def get_colin_users(engine: Engine, corp_nums: List[str]) -> Dict[str, dict]:
    """Fetch filing users from COLIN, keyed by username."""
    if not corp_nums:
        return {}
    results = {}
    chunk_size = 900
    for i in range(0, len(corp_nums), chunk_size):
        chunk = corp_nums[i:i + chunk_size]
        placeholders = ','.join([f"'{c}'" for c in chunk])
        query = f"""
            SELECT DISTINCT 
                upper(u.user_id) as username,
                trim(u.first_nme) as first_name,
                trim(u.last_nme) as last_name,
                u.email_addr as email
            FROM filing_user u
            JOIN event e ON e.event_id = u.event_id
            WHERE e.corp_num IN ({placeholders})
        """
        with engine.connect() as conn:
            result = conn.execute(text(query))
            for r in result.fetchall():
                username = r[0]
                if username:
                    results[username] = {
                        'username': username,
                        'first_name': (r[1] or '').strip().upper() if r[1] else '',
                        'last_name': (r[2] or '').strip().upper() if r[2] else '',
                        'email': (r[3] or '').strip().upper() if r[3] else '',
                    }
    return results


# --- LEAR Queries ---

def get_lear_businesses(engine: Engine, legal_type: str) -> List[dict]:
    query = f"""
        SELECT identifier, legal_name, legal_type, state, founding_date
        FROM businesses
        WHERE identifier LIKE '{legal_type}%'
        ORDER BY identifier
    """
    with engine.connect() as conn:
        result = conn.execute(text(query))
        return [{'corp_num': r[0], 'legal_name': (r[1] or '').strip().upper(),
                 'corp_typ_cd': r[2], 'state': r[3], 'founding_date': r[4]}
                for r in result.fetchall()]


def get_lear_filings(engine: Engine, identifiers: List[str]) -> Dict[str, List[dict]]:
    if not identifiers:
        return {}
    results = defaultdict(list)
    chunk_size = 900
    for i in range(0, len(identifiers), chunk_size):
        chunk = identifiers[i:i + chunk_size]
        placeholders = ','.join([f"'{c}'" for c in chunk])
        query = f"""
            SELECT b.identifier, f.filing_type, f.effective_date, f.paper_only,
                   cei.colin_event_id
            FROM businesses b
            JOIN filings f ON f.business_id = b.id
            LEFT JOIN colin_event_ids cei ON cei.filing_id = f.id
            WHERE b.identifier IN ({placeholders})
              AND f.filing_type != 'lear_tombstone'
            ORDER BY b.identifier, f.effective_date
        """
        with engine.connect() as conn:
            result = conn.execute(text(query))
            for r in result.fetchall():
                results[r[0]].append({
                    'filing_type': r[1],
                    'effective_date': r[2],
                    'paper_only': r[3],
                    'colin_event_id': str(r[4]) if r[4] else None,
                })
    return dict(results)


def get_lear_parties(engine: Engine, identifiers: List[str]) -> Dict[str, List[dict]]:
    if not identifiers:
        return {}
    results = defaultdict(list)
    chunk_size = 900
    for i in range(0, len(identifiers), chunk_size):
        chunk = identifiers[i:i + chunk_size]
        placeholders = ','.join([f"'{c}'" for c in chunk])
        query = f"""
            SELECT b.identifier, p.first_name, p.last_name, pr.role,
                   p.mailing_address_id, p.delivery_address_id,
                   pr.appointment_date, pr.cessation_date
            FROM businesses b
            JOIN party_roles pr ON pr.business_id = b.id
            JOIN parties p ON p.id = pr.party_id
            WHERE b.identifier IN ({placeholders})
            ORDER BY b.identifier, p.last_name
        """
        with engine.connect() as conn:
            result = conn.execute(text(query))
            for r in result.fetchall():
                results[r[0]].append({
                    'first_name': (r[1] or '').strip().upper() if r[1] else '',
                    'last_name': (r[2] or '').strip().upper() if r[2] else '',
                    'role': r[3],
                    'mailing_address_id': str(r[4]) if r[4] else None,
                    'delivery_address_id': str(r[5]) if r[5] else None,
                    'appointment_date': str(r[6])[:10] if r[6] else None,
                    'cessation_date': str(r[7])[:10] if r[7] else None,
                })
    return dict(results)


def get_lear_addresses(engine: Engine, identifiers: List[str]) -> Dict[str, dict]:
    if not identifiers:
        return {}
    results = {}
    chunk_size = 900
    for i in range(0, len(identifiers), chunk_size):
        chunk = identifiers[i:i + chunk_size]
        placeholders = ','.join([f"'{c}'" for c in chunk])
        query = f"""
            SELECT b.identifier, a.id, a.street, a.city, a.postal_code, a.address_type
            FROM businesses b
            JOIN party_roles pr ON pr.business_id = b.id
            JOIN parties p ON p.id = pr.party_id
            JOIN addresses a ON a.id = p.mailing_address_id OR a.id = p.delivery_address_id
            WHERE b.identifier IN ({placeholders})
        """
        with engine.connect() as conn:
            result = conn.execute(text(query))
            for r in result.fetchall():
                # Key by identifier + address_id for lookup
                results[f"{r[0]}_{r[1]}"] = {
                    'street': (r[2] or '').strip().upper() if r[2] else '',
                    'city': (r[3] or '').strip().upper() if r[3] else '',
                    'postal_code': (r[4] or '').strip().upper().replace(' ', '') if r[4] else '',
                    'address_type': r[5],
                }
    return results


def get_lear_offices(engine: Engine, identifiers: List[str]) -> Dict[str, List[dict]]:
    if not identifiers:
        return {}
    results = defaultdict(list)
    chunk_size = 900
    for i in range(0, len(identifiers), chunk_size):
        chunk = identifiers[i:i + chunk_size]
        placeholders = ','.join([f"'{c}'" for c in chunk])
        query = f"""
            SELECT b.identifier, o.office_type
            FROM businesses b
            JOIN offices o ON o.business_id = b.id
            WHERE b.identifier IN ({placeholders})
        """
        with engine.connect() as conn:
            result = conn.execute(text(query))
            for r in result.fetchall():
                results[r[0]].append({
                    'office_type': r[1],
                })
    return dict(results)


def get_lear_aliases(engine: Engine, identifiers: List[str]) -> Dict[str, List[dict]]:
    """Fetch aliases from LEAR."""
    if not identifiers:
        return {}
    results = defaultdict(list)
    chunk_size = 900
    for i in range(0, len(identifiers), chunk_size):
        chunk = identifiers[i:i + chunk_size]
        placeholders = ','.join([f"'{c}'" for c in chunk])
        query = f"""
            SELECT b.identifier, a.alias
            FROM businesses b
            JOIN aliases a ON a.business_id = b.id
            WHERE b.identifier IN ({placeholders})
        """
        with engine.connect() as conn:
            result = conn.execute(text(query))
            for r in result.fetchall():
                results[r[0]].append({
                    'alias': (r[1] or '').strip().upper() if r[1] else '',
                })
    return dict(results)


def get_lear_comments(engine: Engine, identifiers: List[str]) -> Dict[str, List[dict]]:
    """Fetch business comments from LEAR."""
    if not identifiers:
        return {}
    results = defaultdict(list)
    chunk_size = 900
    for i in range(0, len(identifiers), chunk_size):
        chunk = identifiers[i:i + chunk_size]
        placeholders = ','.join([f"'{c}'" for c in chunk])
        query = f"""
            SELECT b.identifier, c.comment
            FROM businesses b
            JOIN comments c ON c.business_id = b.id
            WHERE b.identifier IN ({placeholders})
              AND c.filing_id IS NULL
        """
        with engine.connect() as conn:
            result = conn.execute(text(query))
            for r in result.fetchall():
                comment_text = (r[1] or '').strip().upper() if r[1] else ''
                if comment_text:
                    results[r[0]].append({
                        'comment': comment_text,
                    })
    return dict(results)


def get_lear_filing_comments(engine: Engine, identifiers: List[str]) -> Dict[str, List[dict]]:
    """Fetch filing-level comments from LEAR."""
    if not identifiers:
        return {}
    results = defaultdict(list)
    chunk_size = 900
    for i in range(0, len(identifiers), chunk_size):
        chunk = identifiers[i:i + chunk_size]
        placeholders = ','.join([f"'{c}'" for c in chunk])
        query = f"""
            SELECT b.identifier, c.comment
            FROM businesses b
            JOIN comments c ON c.business_id = b.id
            WHERE b.identifier IN ({placeholders})
              AND c.filing_id IS NOT NULL
        """
        with engine.connect() as conn:
            result = conn.execute(text(query))
            for r in result.fetchall():
                comment_text = (r[1] or '').strip().upper() if r[1] else ''
                if comment_text:
                    results[r[0]].append({
                        'comment': comment_text,
                    })
    return dict(results)


def get_lear_users(engine: Engine, identifiers: List[str]) -> Dict[str, dict]:
    """Fetch users from LEAR that are linked to the given businesses via filings.submitter_id.
    """
    if not identifiers:
        return {}
    results = {}
    chunk_size = 900
    for i in range(0, len(identifiers), chunk_size):
        chunk = identifiers[i:i + chunk_size]
        placeholders = ','.join([f"'{c}'" for c in chunk])
        query = f"""
            SELECT DISTINCT
                upper(u.username) as username,
                trim(u.firstname) as first_name,
                trim(u.lastname) as last_name,
                u.email as email
            FROM businesses b
            JOIN filings f ON f.business_id = b.id
            JOIN users u   ON u.id = f.submitter_id
            WHERE b.identifier IN ({placeholders})
              AND u.username IS NOT NULL
        """
        with engine.connect() as conn:
            result = conn.execute(text(query))
            for r in result.fetchall():
                username = r[0]
                if username:
                    results[username] = {
                        'username': username,
                        'first_name': (r[1] or '').strip().upper() if r[1] else '',
                        'last_name': (r[2] or '').strip().upper() if r[2] else '',
                        'email': (r[3] or '').strip().upper() if r[3] else '',
                    }
    return results


# --- Verification Tasks ---

@task(name='Verify-Businesses', cache_policy=NO_CACHE)
def verify_businesses(colin_data: List[dict], lear_data: List[dict]) -> List[VerificationResult]:
    results = []
    lear_map = {b['corp_num']: b for b in lear_data}

    for colin_biz in colin_data:
        corp_num = colin_biz['corp_num']
        lear_biz = lear_map.get(corp_num)

        if not lear_biz:
            results.append(VerificationResult(corp_num, 'businesses', 'identifier', corp_num, 'MISSING', 'MISSING_IN_LEAR'))
            continue

        colin_name = colin_biz['legal_name']
        lear_name = lear_biz['legal_name']

        # add suffix to colin buisness name if exist
        if CORP_NAME_SUFFIX:
            colin_name = f"{colin_name}{CORP_NAME_SUFFIX}".strip().upper()

        
        # Name
        if colin_name == lear_name:
            results.append(VerificationResult(corp_num, 'businesses', 'legal_name', colin_name, lear_name, 'MATCH'))
        else:
            results.append(VerificationResult(corp_num, 'businesses', 'legal_name', colin_name, lear_name, 'MISMATCH'))

        # Type
        if colin_biz['corp_typ_cd'] == lear_biz['corp_typ_cd']:
            results.append(VerificationResult(corp_num, 'businesses', 'legal_type', colin_biz['corp_typ_cd'], lear_biz['corp_typ_cd'], 'MATCH'))
        else:
            results.append(VerificationResult(corp_num, 'businesses', 'legal_type', colin_biz['corp_typ_cd'], lear_biz['corp_typ_cd'], 'MISMATCH'))

        # State
        expected_state = STATE_MAP.get(colin_biz.get('state_typ_cd', ''), '')
        if expected_state == lear_biz.get('state', ''):
            results.append(VerificationResult(corp_num, 'businesses', 'state', colin_biz.get('state_typ_cd'), lear_biz.get('state'), 'MATCH'))
        else:
            results.append(VerificationResult(corp_num, 'businesses', 'state', colin_biz.get('state_typ_cd'), lear_biz.get('state'), 'MISMATCH'))

        # Date
        colin_date = colin_biz.get('recognition_dts')
        lear_date = lear_biz.get('founding_date')
        if colin_date is None and lear_date is not None:
            results.append(VerificationResult(corp_num, 'businesses', 'founding_date', 'NULL', str(lear_date), 'EXPECTED_GAP', 'COLIN date is NULL'))
        elif colin_date is not None and lear_date is not None:
            colin_date_str = str(colin_date)[:10]
            lear_date_str = str(lear_date)[:10]
            if colin_date_str == lear_date_str:
                results.append(VerificationResult(corp_num, 'businesses', 'founding_date', colin_date_str, lear_date_str, 'MATCH'))
            else:
                results.append(VerificationResult(corp_num, 'businesses', 'founding_date', colin_date_str, lear_date_str, 'MISMATCH'))
        elif colin_date is None and lear_date is None:
            results.append(VerificationResult(corp_num, 'businesses', 'founding_date', 'NULL', 'NULL', 'MATCH'))

    # Check for corps in LEAR but not in COLIN
    colin_corps = {b['corp_num'] for b in colin_data}
    for lear_biz in lear_data:
        if lear_biz['corp_num'] not in colin_corps:
            results.append(VerificationResult(lear_biz['corp_num'], 'businesses', 'identifier', 'MISSING', lear_biz['corp_num'], 'MISSING_IN_COLIN'))

    return results


@task(name='Verify-Filings', cache_policy=NO_CACHE)
def verify_filings(colin_filings: Dict[str, List[dict]], lear_filings: Dict[str, List[dict]]) -> List[VerificationResult]:
    results = []
    all_corps = set(list(colin_filings.keys()) + list(lear_filings.keys()))

    for corp_num in sorted(all_corps):
        colin_files = colin_filings.get(corp_num, [])
        lear_files = lear_filings.get(corp_num, [])

        # Count
        if len(colin_files) == len(lear_files):
            results.append(VerificationResult(corp_num, 'filings', 'count', len(colin_files), len(lear_files), 'MATCH'))
        else:
            results.append(VerificationResult(corp_num, 'filings', 'count', len(colin_files), len(lear_files), 'MISMATCH'))

        # Event ID cross-check
        lear_event_ids = {f['colin_event_id'] for f in lear_files if f.get('colin_event_id')}
        colin_event_ids = {f['event_id'] for f in colin_files}

        missing_in_lear = colin_event_ids - lear_event_ids
        for eid in missing_in_lear:
            results.append(VerificationResult(corp_num, 'filings', 'event_id', eid, 'MISSING', 'MISSING_IN_LEAR'))

        # Type mapping check
        for colin_f in colin_files:
            colin_type = colin_f['filing_typ_cd']
            expected_lear_type = FILING_TYPE_MAP.get(colin_type, 'UNMAPPED')
            lear_f = next((f for f in lear_files if f.get('colin_event_id') == colin_f['event_id']), None)

            if lear_f is None:
                continue

            if expected_lear_type == 'UNMAPPED':
                results.append(VerificationResult(corp_num, 'filings', 'filing_type', colin_type, lear_f['filing_type'], 'MISMATCH', 'No mapping'))
            elif expected_lear_type == lear_f['filing_type']:
                results.append(VerificationResult(corp_num, 'filings', 'filing_type', colin_type, lear_f['filing_type'], 'MATCH'))
            else:
                results.append(VerificationResult(corp_num, 'filings', 'filing_type', colin_type, lear_f['filing_type'], 'MISMATCH'))

            # Paper only
            expected_paper = colin_f.get('ods_type_cd', '') == 'P'
            actual_paper = bool(lear_f.get('paper_only', False))
            if expected_paper == actual_paper:
                results.append(VerificationResult(corp_num, 'filings', 'paper_only', expected_paper, actual_paper, 'MATCH'))
            else:
                results.append(VerificationResult(corp_num, 'filings', 'paper_only', expected_paper, actual_paper, 'MISMATCH'))

    return results


@task(name='Verify-Parties', cache_policy=NO_CACHE)
def verify_parties(colin_parties: Dict[str, List[dict]], lear_parties: Dict[str, List[dict]]) -> List[VerificationResult]:
    results = []
    all_corps = set(list(colin_parties.keys()) + list(lear_parties.keys()))

    for corp_num in sorted(all_corps):
        colin_ps = colin_parties.get(corp_num, [])
        lear_ps = lear_parties.get(corp_num, [])

        if len(colin_ps) == len(lear_ps):
            results.append(VerificationResult(corp_num, 'parties', 'count', len(colin_ps), len(lear_ps), 'MATCH'))
        else:
            results.append(VerificationResult(corp_num, 'parties', 'count', len(colin_ps), len(lear_ps), 'MISMATCH'))

        # Match by name
        lear_name_set = {(p['first_name'], p['last_name']) for p in lear_ps}
        for colin_p in colin_ps:
            colin_key = (colin_p['first_nme'], colin_p['last_nme'])
            if colin_key in lear_name_set:
                results.append(VerificationResult(corp_num, 'parties', 'name', f'{colin_p["first_nme"]} {colin_p["last_nme"]}', f'{colin_p["first_nme"]} {colin_p["last_nme"]}', 'MATCH'))
            else:
                results.append(VerificationResult(corp_num, 'parties', 'name', f'{colin_p["first_nme"]} {colin_p["last_nme"]}', 'NOT FOUND', 'MISSING_IN_LEAR'))

            # Role check
            expected_role = ROLE_MAP.get(colin_p['party_typ_cd'], 'unknown')
            lear_p = next((p for p in lear_ps if p['first_name'] == colin_p['first_nme'] and p['last_name'] == colin_p['last_nme']), None)
            if lear_p:
                if expected_role == lear_p['role']:
                    results.append(VerificationResult(corp_num, 'parties', 'role', colin_p['party_typ_cd'], lear_p['role'], 'MATCH'))
                else:
                    results.append(VerificationResult(corp_num, 'parties', 'role', colin_p['party_typ_cd'], lear_p['role'], 'MISMATCH'))

                # Appointment date check
                colin_appt = colin_p.get('appointment_dt')
                lear_appt = lear_p.get('appointment_date')
                if colin_appt and lear_appt:
                    if colin_appt == lear_appt:
                        results.append(VerificationResult(corp_num, 'parties', 'appointment_date', colin_appt, lear_appt, 'MATCH'))
                    else:
                        results.append(VerificationResult(corp_num, 'parties', 'appointment_date', colin_appt, lear_appt, 'MISMATCH'))
                elif not colin_appt and not lear_appt:
                    results.append(VerificationResult(corp_num, 'parties', 'appointment_date', 'NULL', 'NULL', 'MATCH'))

                # Cessation date check
                colin_cess = colin_p.get('cessation_dt')
                lear_cess = lear_p.get('cessation_date')
                if colin_cess and lear_cess:
                    if colin_cess == lear_cess:
                        results.append(VerificationResult(corp_num, 'parties', 'cessation_date', colin_cess, lear_cess, 'MATCH'))
                    else:
                        results.append(VerificationResult(corp_num, 'parties', 'cessation_date', colin_cess, lear_cess, 'MISMATCH'))
                elif not colin_cess and not lear_cess:
                    results.append(VerificationResult(corp_num, 'parties', 'cessation_date', 'NULL', 'NULL', 'MATCH'))
                elif colin_cess and not lear_cess:
                    results.append(VerificationResult(corp_num, 'parties', 'cessation_date', colin_cess, 'NULL', 'MISSING_IN_LEAR'))
                elif not colin_cess and lear_cess:
                    results.append(VerificationResult(corp_num, 'parties', 'cessation_date', 'NULL', lear_cess, 'EXTRA_IN_LEAR'))

    return results


@task(name='Verify-Addresses', cache_policy=NO_CACHE)
def verify_addresses(colin_addrs: Dict[Tuple[str, str], dict], lear_addrs: Dict[str, dict]) -> List[VerificationResult]:
    results = []

    colin_by_corp = defaultdict(int)
    for (corp_num, addr_id) in colin_addrs.keys():
        colin_by_corp[corp_num] += 1

    lear_by_corp = defaultdict(int)
    for key in lear_addrs.keys():
        corp_num = key.split('_')[0]
        lear_by_corp[corp_num] += 1

    all_corps = set(list(colin_by_corp.keys()) + list(lear_by_corp.keys()))
    for corp_num in sorted(all_corps):
        colin_count = colin_by_corp.get(corp_num, 0)
        lear_count = lear_by_corp.get(corp_num, 0)
        # lear creates mailing and delievery address for each colin address, so it contains 2 times the addresses in colin
        if (colin_count * 2) == lear_count: 
            results.append(VerificationResult(corp_num, 'addresses', 'count', colin_count, lear_count, 'MATCH', 'COLIN stores unique addresses, LEAR duplicates for mailing/delivery, so double the count in LEAR is expected.'))
        else:
            results.append(VerificationResult(corp_num, 'addresses', 'count', colin_count, lear_count, 'MISMATCH'))

    # Build a lookup of LEAR addresses by (corp_num, street, city, postal_code)
    lear_lookup = {}
    for key, lear_addr in lear_addrs.items():
        corp_num = key.split('_')[0]
        map_key = (corp_num, lear_addr['street'], lear_addr['city'], lear_addr['postal_code'])
        lear_lookup[map_key] = lear_addr

    for (corp_num, colin_addr_id), colin_addr in colin_addrs.items():
        colin_key = (corp_num, colin_addr['street'], colin_addr['city'], colin_addr['postal_cd'])
        lear_addr = lear_lookup.get(colin_key)

        if lear_addr:
            results.append(VerificationResult(corp_num, 'addresses', 'street', colin_addr['street'], lear_addr['street'], 'MATCH'))
            results.append(VerificationResult(corp_num, 'addresses', 'city', colin_addr['city'], lear_addr['city'], 'MATCH'))
            results.append(VerificationResult(corp_num, 'addresses', 'postal_code', colin_addr['postal_cd'], lear_addr['postal_code'], 'MATCH'))
        else:
            results.append(VerificationResult(corp_num, 'addresses', 'street', colin_addr['street'], 'NOT FOUND', 'MISSING_IN_LEAR'))

    return results


@task(name='Verify-Offices', cache_policy=NO_CACHE)
def verify_offices(colin_offices: Dict[str, List[dict]], lear_offices: Dict[str, List[dict]]) -> List[VerificationResult]:
    results = []
    all_corps = set(list(colin_offices.keys()) + list(lear_offices.keys()))

    for corp_num in sorted(all_corps):
        colin_offs = colin_offices.get(corp_num, [])
        lear_offs = lear_offices.get(corp_num, [])

        if len(colin_offs) == len(lear_offs):
            results.append(VerificationResult(corp_num, 'offices', 'count', len(colin_offs), len(lear_offs), 'MATCH'))
        else:
            results.append(VerificationResult(corp_num, 'offices', 'count', len(colin_offs), len(lear_offs), 'MISMATCH'))

    return results


@task(name='Verify-Aliases', cache_policy=NO_CACHE)
def verify_aliases(colin_aliases: Dict[str, List[dict]], lear_aliases: Dict[str, List[dict]]) -> List[VerificationResult]:
    """Compare aliases between COLIN and LEAR."""
    results = []
    all_corps = set(list(colin_aliases.keys()) + list(lear_aliases.keys()))

    for corp_num in sorted(all_corps):
        colin_aliases_list = colin_aliases.get(corp_num, [])
        lear_aliases_list = lear_aliases.get(corp_num, [])

        # Count comparison
        if len(colin_aliases_list) == len(lear_aliases_list):
            results.append(VerificationResult(corp_num, 'aliases', 'count', len(colin_aliases_list), len(lear_aliases_list), 'MATCH'))
        else:
            results.append(VerificationResult(corp_num, 'aliases', 'count', len(colin_aliases_list), len(lear_aliases_list), 'MISMATCH'))

        # Match by alias name
        lear_alias_set = {a['alias'] for a in lear_aliases_list}
        for colin_alias in colin_aliases_list:
            alias_name = colin_alias['alias']
            if alias_name in lear_alias_set:
                results.append(VerificationResult(corp_num, 'aliases', 'alias', alias_name, alias_name, 'MATCH'))
            else:
                results.append(VerificationResult(corp_num, 'aliases', 'alias', alias_name, 'NOT FOUND', 'MISSING_IN_LEAR'))

    return results


@task(name='Verify-Comments', cache_policy=NO_CACHE)
def verify_comments(colin_comments: Dict[str, List[dict]], lear_comments: Dict[str, List[dict]]) -> List[VerificationResult]:
    """Compare business comments between COLIN and LEAR."""
    results = []
    all_corps = set(list(colin_comments.keys()) + list(lear_comments.keys()))

    for corp_num in sorted(all_corps):
        colin_comments_list = colin_comments.get(corp_num, [])
        lear_comments_list = lear_comments.get(corp_num, [])

        # Count comparison
        if len(colin_comments_list) == len(lear_comments_list):
            results.append(VerificationResult(corp_num, 'comments', 'count', len(colin_comments_list), len(lear_comments_list), 'MATCH'))
        else:
            results.append(VerificationResult(corp_num, 'comments', 'count', len(colin_comments_list), len(lear_comments_list), 'MISMATCH'))

        # Match by comment text (first 200 chars for comparison)
        lear_comment_set = {c['comment'][:200] for c in lear_comments_list}
        for colin_comment in colin_comments_list:
            comment_text = colin_comment['comment'][:200]
            if comment_text in lear_comment_set:
                results.append(VerificationResult(corp_num, 'comments', 'comment', comment_text, comment_text, 'MATCH'))
            else:
                results.append(VerificationResult(corp_num, 'comments', 'comment', comment_text, 'NOT FOUND', 'MISSING_IN_LEAR'))

    return results


@task(name='Verify-Filing-Comments', cache_policy=NO_CACHE)
def verify_filing_comments(colin_comments: Dict[str, List[dict]], lear_comments: Dict[str, List[dict]]) -> List[VerificationResult]:
    """Compare filing-level comments between COLIN and LEAR."""
    results = []
    all_corps = set(list(colin_comments.keys()) + list(lear_comments.keys()))

    for corp_num in sorted(all_corps):
        colin_comments_list = colin_comments.get(corp_num, [])
        lear_comments_list = lear_comments.get(corp_num, [])

        # Count comparison
        if len(colin_comments_list) == len(lear_comments_list):
            results.append(VerificationResult(corp_num, 'filing_comments', 'count', len(colin_comments_list), len(lear_comments_list), 'MATCH'))
        else:
            results.append(VerificationResult(corp_num, 'filing_comments', 'count', len(colin_comments_list), len(lear_comments_list), 'MISMATCH'))

        # Match by comment text (first 200 chars for comparison)
        lear_comment_set = {c['comment'][:200] for c in lear_comments_list}
        for colin_comment in colin_comments_list:
            comment_text = colin_comment['comment'][:200]
            if comment_text in lear_comment_set:
                results.append(VerificationResult(corp_num, 'filing_comments', 'comment', comment_text, comment_text, 'MATCH'))
            else:
                results.append(VerificationResult(corp_num, 'filing_comments', 'comment', comment_text, 'NOT FOUND', 'MISSING_IN_LEAR'))

    return results


@task(name='Verify-Users', cache_policy=NO_CACHE)
def verify_users(colin_users: Dict[str, dict], lear_users: Dict[str, dict]) -> List[VerificationResult]:
    """Compare filing users between COLIN and LEAR."""

    results = []
    all_usernames = set(list(colin_users.keys()) + list(lear_users.keys()))

    def _norm(v: str) -> str:
        """Normalize a value for both comparison and display."""
        if v is None:
            return ''
        return v.strip().upper() if isinstance(v, str) else str(v)

    def _display(v: str) -> str:
        """Display form for the CSV - empty becomes 'NULL' for readability."""
        n = _norm(v)
        return n if n else 'NULL'

    for username in sorted(all_usernames):
        colin_user = colin_users.get(username)
        lear_user = lear_users.get(username)

        if not lear_user:
            results.append(VerificationResult(username, 'users', 'username', username, 'MISSING', 'MISSING_IN_LEAR'))
            continue

        if not colin_user:
            results.append(VerificationResult(username, 'users', 'username', 'MISSING', username, 'MISSING_IN_COLIN'))
            continue

        results.append(VerificationResult(username, 'users', 'username', username, username, 'MATCH'))

        # Compare each field, treating NULL/empty explicitly as 'NULL'
        for field in ('first_name', 'last_name', 'email'):
            colin_val = _norm(colin_user.get(field))
            lear_val = _norm(lear_user.get(field))
            if colin_val == lear_val:
                if not colin_val:
                    results.append(VerificationResult(
                        username, 'users', field,
                        'NULL', 'NULL', 'MATCH', 'Both sides NULL',
                    ))
                else:
                    results.append(VerificationResult(
                        username, 'users', field,
                        colin_val, lear_val, 'MATCH',
                    ))
            else:
                results.append(VerificationResult(
                    username, 'users', field,
                    _display(colin_user.get(field)),
                    _display(lear_user.get(field)),
                    'MISMATCH',
                ))

    return results


@task(name='Generate-Report', cache_policy=NO_CACHE)
def generate_report(results: List[VerificationResult], output_path: str):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['corp_num', 'table', 'field', 'colin_value', 'lear_value', 'status', 'notes'])
        writer.writeheader()
        for r in results:
            writer.writerow(r.to_dict())

    status_counts = defaultdict(int)
    table_status_counts = defaultdict(lambda: defaultdict(int))

    for r in results:
        status_counts[r.status] += 1
        table_status_counts[r.table][r.status] += 1

    total = len(results)
    matches = status_counts['MATCH']
    mismatches = status_counts['MISMATCH']
    missing_lear = status_counts['MISSING_IN_LEAR']
    missing_colin = status_counts['MISSING_IN_COLIN']
    expected_gaps = status_counts['EXPECTED_GAP']

    print('\n' + '=' * 80)
    print('📊 MIGRATION VERIFICATION SUMMARY')
    print('=' * 80)
    print(f'Total checks performed:  {total}')
    print(f'✅ Matches:              {matches}')
    print(f'❌ Mismatches:           {mismatches}')
    print(f'⚠️  Missing in LEAR:      {missing_lear}')
    print(f'⚠️  Missing in COLIN:     {missing_colin}')
    print(f'ℹ️  Expected gaps:        {expected_gaps}')
    print()

    for table_name in sorted(table_status_counts.keys()):
        counts = table_status_counts[table_name]
        print(f'  {table_name}:')
        for status in ['MATCH', 'MISMATCH', 'MISSING_IN_LEAR', 'MISSING_IN_COLIN', 'EXPECTED_GAP']:
            if counts[status] > 0:
                print(f'    {status}: {counts[status]}')
        print()

    if mismatches > 0 or missing_lear > 0:
        print('❌ VERIFICATION FAILED - See CSV report for details.')
    else:
        print('✅ VERIFICATION PASSED - All checks matched!')

    print(f'\n📄 Full report saved to: {output_path}')
    print('=' * 80 + '\n')


@flow(name='Verify-Migration-Flow', log_prints=True, persist_result=False)
def verify_migration_flow():
    print(f'🚀 Starting migration verification for entity type: {VERIFY_LEGAL_TYPE}...\n')

    config = get_config()

    print('🔌 Connecting to COLIN Oracle...')
    colin_engine = colin_oracle_init(config)
    print('✅ Connected to COLIN Oracle')

    print('🔌 Connecting to LEAR Business DB...')
    lear_engine = lear_init(config)
    print('✅ Connected to LEAR Business DB')

    # Fetch COLIN data
    print('\n📥 Fetching data from COLIN Oracle...')
    colin_businesses = get_colin_businesses(colin_engine, VERIFY_LEGAL_TYPE)
    print(f'   Found {len(colin_businesses)} businesses in COLIN')

    
    colin_corp_nums = [b['corp_num'] for b in colin_businesses]
    colin_filings = get_colin_filings(colin_engine, colin_corp_nums)
    print(f'   Found {sum(len(v) for v in colin_filings.values())} filings in COLIN')
    
    colin_parties = get_colin_parties(colin_engine, colin_corp_nums)
    print(f'   Found {sum(len(v) for v in colin_parties.values())} parties in COLIN')
    
    colin_addrs = get_colin_addresses(colin_engine, colin_corp_nums)
    print(f'   Found {len(colin_addrs)} addresses in COLIN')
    
    colin_offices = get_colin_offices(colin_engine, colin_corp_nums)
    print(f'   Found {sum(len(v) for v in colin_offices.values())} offices in COLIN')
    
    colin_aliases = get_colin_aliases(colin_engine, colin_corp_nums)
    print(f'   Found {sum(len(v) for v in colin_aliases.values())} aliases in COLIN')
    
    colin_comments = get_colin_comments(colin_engine, colin_corp_nums)
    print(f'   Found {sum(len(v) for v in colin_comments.values())} business comments in COLIN')

    # get ledger text comments (filing comments) from COLIN
    colin_filing_comments = get_colin_filing_comments(colin_engine, colin_corp_nums)
    print(f'   Found {sum(len(v) for v in colin_filing_comments.values())} filing comments (ledger notations) in COLIN')
    
    colin_users = get_colin_users(colin_engine, colin_corp_nums)
    print(f'   Found {len(colin_users)} filing users in COLIN')
    


    # Fetch LEAR data
    print('\n📥 Fetching data from LEAR Business DB...')
    lear_businesses = get_lear_businesses(lear_engine, VERIFY_LEGAL_TYPE)
    print(f'   Found {len(lear_businesses)} businesses in LEAR')

    
    lear_corp_nums = [b['corp_num'] for b in lear_businesses]
    lear_filings = get_lear_filings(lear_engine, lear_corp_nums)
    print(f'   Found {sum(len(v) for v in lear_filings.values())} filings in LEAR')
    
    lear_parties = get_lear_parties(lear_engine, lear_corp_nums)
    print(f'   Found {sum(len(v) for v in lear_parties.values())} parties in LEAR')
    
    lear_addrs = get_lear_addresses(lear_engine, lear_corp_nums)
    print(f'   Found {len(lear_addrs)} addresses in LEAR')
    
    lear_offices = get_lear_offices(lear_engine, lear_corp_nums)
    print(f'   Found {sum(len(v) for v in lear_offices.values())} offices in LEAR')
    
    lear_aliases = get_lear_aliases(lear_engine, lear_corp_nums)
    print(f'   Found {sum(len(v) for v in lear_aliases.values())} aliases in LEAR')
    
    lear_comments = get_lear_comments(lear_engine, lear_corp_nums)
    print(f'   Found {sum(len(v) for v in lear_comments.values())} business comments in LEAR')

    # ledger text comments 
    lear_filing_comments = get_lear_filing_comments(lear_engine, lear_corp_nums)
    print(f'   Found {sum(len(v) for v in lear_filing_comments.values())} filing comments in LEAR')
    
    lear_users = get_lear_users(lear_engine, lear_corp_nums)
    print(f'   Found {len(lear_users)} filing users in LEAR')
    
    # Run comparisons
    print('\n🔍 Running comparisons...')
    all_results = []

    all_results.extend(verify_businesses(colin_businesses, lear_businesses))
    all_results.extend(verify_filings(colin_filings, lear_filings))
    all_results.extend(verify_parties(colin_parties, lear_parties))
    all_results.extend(verify_addresses(colin_addrs, lear_addrs))
    all_results.extend(verify_offices(colin_offices, lear_offices))
    all_results.extend(verify_aliases(colin_aliases, lear_aliases))
    all_results.extend(verify_comments(colin_comments, lear_comments))
    all_results.extend(verify_filing_comments(colin_filing_comments, lear_filing_comments))
    all_results.extend(verify_users(colin_users, lear_users))
    
    generate_report(all_results, OUTPUT_CSV_PATH)

    colin_engine.dispose()
    lear_engine.dispose()
    print('🏁 Verification complete!')


if __name__ == '__main__':
    verify_migration_flow()