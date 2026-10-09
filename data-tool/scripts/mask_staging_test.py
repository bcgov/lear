"""
Mask PII in staging databases before migration flows read them.

Current scope : individual names (Faker), emails, phones, addresses
Fields that are NULL or empty in the original data are NOT masked.

Environment selection comes from .env:
- DATABASE_NAME_COLIN_MIGR     : which staging DB to mask (must also appear in
                                 ALLOWED_MASKING_DB, a comma-separated allowlist;
                                 prod or anything else is refused)
- ALLOWED_ENTITIES_TO_MASK     : comma-separated corp types (e.g. RLY,CEM).
                                 Empty/unset = mask the whole staging DB.
- ALLOWED_MASKING_DB           : comma-separated allowlist of DB names that can be masked.                                 

Usage:
    make mask-staging-test MASK_DRY_RUN=1   # dry-run
    make mask-staging-test                  # updates data

Safety:
- Refuses any database not listed in ALLOWED_MASKING_DB.
- Prompts for confirmation before a live run.
- Idempotent: masked values are recorded in mig_masking_map, re-runs reuse them.
- Deterministic: the same source key always yields the same masked name
  (Faker seeded from the key).
"""
import hashlib
import sys
from datetime import datetime, timezone

from faker import Faker
import psycopg2

# ---------------------------------------------------------------------------
# test values (single email / single phone).
# ---------------------------------------------------------------------------
TEST_EMAIL = 'dev.test@gov.bc.ca'
TEST_PHONE = '555-555-5555'

# test addresses
TEST_ADDRESSES = [
    ('100 Test Street', None, None, 'Victoria', 'BC', 'V8V1X1', 'CA', 'Test', 'Street'),
    ('200 Sample Avenue', 'Suite 201', None, 'Vancouver', 'BC', 'V5K0A1', 'CA', 'Sample', 'Avenue'),
    ('300 Mock Road', None, None, 'Kamloops', 'BC', 'V2C1A1', 'CA', 'Mock', 'Road'),
    ('400 Placeholder Way', 'Unit 4', None, 'Prince George', 'BC', 'V2K1B2', 'CA', 'Placeholder', 'Way'),
    ('500 Example Crescent', None, None, 'Nanaimo', 'BC', 'V9R1C3', 'CA', 'Example', 'Crescent'),
    ('600 Fixture Lane', 'Bay 6', None, 'Kelowna', 'BC', 'V1Y1D4', 'CA', 'Fixture', 'Lane'),
    ('700 Trial Boulevard', None, None, 'Surrey', 'BC', 'V3R1E5', 'CA', 'Trial', 'Boulevard'),
    ('800 Demo Drive', None, None, 'Cranbrook', 'BC', 'V1C1F6', 'CA', 'Demo', 'Drive'),
]

DEFAULT_ALLOWED_DBS = ['colin-staging', 'colin-staging-test']

# ---------------------------------------------------------------------------
# Masking rules: table -> (key columns, {column: rule})
# rule: 'first_name' | 'last_name' | 'middle_name' | 'email' | 'phone'
#       | 'address' (whole-address unit)
# Candidate columns are intersected with the table's real columns at runtime,
# so a rule simply does nothing for a table that lacks the column.
# ---------------------------------------------------------------------------
NAME_COLS = ['first_name', 'first_nme', 'middle_name', 'middle_nme',
             'last_name', 'last_nme',
             'notify_first_nme', 'notify_middle_nme', 'notify_last_nme']
EMAIL_COLS = ['email_addr', 'email_req_address', 'email_address', 'admin_email']
PHONE_COLS = ['phone_number']


def name_rule(col):
    if 'first' in col:
        return 'first_name'
    if 'middle' in col:
        return 'middle_name'
    return 'last_name'


RULES = {
    'corp_party': (
        ['corp_party_id'],
        {**{c: name_rule(c) for c in NAME_COLS}, 'phone': 'phone',
         'email_address': 'email'},
    ),
    'filing_user': (
        ['event_id', 'user_id'],
        {**{c: name_rule(c) for c in NAME_COLS}, 'email_addr': 'email'},
    ),
    'completing_party': (
        ['event_id'],
        {**{c: name_rule(c) for c in NAME_COLS},
         **{c: 'email' for c in EMAIL_COLS}},
    ),
    'submitting_party': (
        ['event_id'],
        {**{c: name_rule(c) for c in NAME_COLS},
         **{c: 'email' for c in EMAIL_COLS},
         **{c: 'phone' for c in PHONE_COLS},
         'pickup_by': 'full_name'},
    ),
    'notification': (
        ['event_id'],
        {**{c: name_rule(c) for c in NAME_COLS},
         **{c: 'email' for c in EMAIL_COLS},
         **{c: 'phone' for c in PHONE_COLS},
         'pickup_by': 'full_name'},
    ),
    'notification_resend': (
        ['event_id'],
        {**{c: name_rule(c) for c in NAME_COLS},
         **{c: 'email' for c in EMAIL_COLS},
         **{c: 'phone' for c in PHONE_COLS},
         'pickup_by': 'full_name'},
    ),
    'party_notification': (
        ['party_id'],
        {**{c: name_rule(c) for c in NAME_COLS},
         **{c: 'email' for c in EMAIL_COLS},
         **{c: 'phone' for c in PHONE_COLS},
         'pickup_by': 'full_name'},
    ),
    'corp_comments': (
        ['corp_num', 'comment_dts'],
        {c: name_rule(c) for c in NAME_COLS},
    ),
    'address': (
        ['addr_id'],
        {'addr_line_1': 'address', 'addr_line_2': 'address', 'addr_line_3': 'address',
         'city': 'address', 'province': 'address', 'postal_cd': 'address',
         'country_typ_cd': 'address', 'street_name': 'address',
         'street_type': 'address', 'street_direction': 'address'},
    ),
    'corporation': (
        ['corp_num'],
        {'admin_email': 'email'},
    ),
}

ADDRESS_PART = {'addr_line_1': 0, 'addr_line_2': 1, 'addr_line_3': 2,
                'city': 3, 'province': 4, 'postal_cd': 5, 'country_typ_cd': 6,
                'street_name': 7, 'street_type': 8, 'street_direction': None}


def stable_int(key: str) -> int:
    return int(hashlib.sha256(key.encode()).hexdigest(), 16)


def fake_name(rule: str, key: str) -> str:
    f = Faker()
    f.seed_instance(stable_int(key))
    first = f.first_name()
    if rule == 'first_name':
        return first
    if rule == 'last_name':
        return f.last_name()
    middle = f.first_name()  # middle_name: distinct from the first name
    while middle == first:
        middle = f.first_name()
    return middle


def masked_value_for(rule: str, col: str, key: str):
    if rule == 'email':
        return TEST_EMAIL
    if rule == 'phone':
        return TEST_PHONE
    if rule == 'address':
        part = ADDRESS_PART[col]
        if part is None:  # e.g. street_direction: no pooled value -> write NULL
            return None
        return TEST_ADDRESSES[stable_int(key) % len(TEST_ADDRESSES)][part]
    if rule == 'full_name':
        f = Faker()
        f.seed_instance(stable_int(key))
        return f.name()
    return fake_name(rule, key)


class OwnerResolver:
    """Resolves (entity_type, corp_num) for a masked row, with caching."""

    def __init__(self, cur):
        self.cur = cur
        self.cache = {}

    def _corp(self, corp_num):
        if corp_num not in self.cache:
            self.cur.execute("SELECT corp_type_cd FROM corporation WHERE corp_num=%s",
                             (corp_num,))
            hit = self.cur.fetchone()
            self.cache[corp_num] = (hit[0] if hit else None, corp_num)
        return self.cache[corp_num]

    def resolve(self, table, cols_list, row):
        if table == 'corporation':
            return self._corp(row[cols_list.index('corp_num')])
        if 'corp_num' in cols_list:
            return self._corp(row[cols_list.index('corp_num')])
        if 'event_id' in cols_list:
            eid = str(row[cols_list.index('event_id')])
            if eid not in self.cache:
                self.cur.execute("SELECT corp_num FROM event WHERE event_id=%s", (eid,))
                hit = self.cur.fetchone()
                self.cache[eid] = self._corp(hit[0]) if hit else (None, None)
            return self.cache[eid]
        if 'party_id' in cols_list:
            pid = str(row[cols_list.index('party_id')])
            if pid not in self.cache:
                self.cur.execute("SELECT corp_num FROM corp_party WHERE corp_party_id=%s", (pid,))
                hit = self.cur.fetchone()
                self.cache[pid] = self._corp(hit[0]) if hit else (None, None)
            return self.cache[pid]
        if table == 'address':
            aid = str(row[cols_list.index('addr_id')])
            if aid not in self.cache:
                self.cur.execute("""
                    SELECT MIN(corp_num) FROM (
                        SELECT corp_num FROM corp_party
                          WHERE mailing_addr_id=%s OR delivery_addr_id=%s
                        UNION
                        SELECT corp_num FROM office
                          WHERE mailing_addr_id=%s OR delivery_addr_id=%s) t
                """, (aid, aid, aid, aid))
                hit = self.cur.fetchone()
                self.cache[aid] = self._corp(hit[0]) if hit and hit[0] else (None, None)
            return self.cache[aid]
        return (None, None)


def ensure_map_table(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mig_masking_map (
            source_table   varchar(100) NOT NULL,
            source_key     varchar(200) NOT NULL,
            column_name    varchar(100) NOT NULL,
            original_value text,
            masked_value   text NOT NULL,
            entity_type    varchar(10),
            corp_num       varchar(20),
            created_at     timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (source_table, source_key, column_name)
        )
    """)
    cur.execute("ALTER TABLE mig_masking_map ADD COLUMN IF NOT EXISTS entity_type varchar(10)")
    cur.execute("ALTER TABLE mig_masking_map ADD COLUMN IF NOT EXISTS corp_num varchar(20)")


def table_columns(cur, table):
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=%s", (table,))
    return {r[0] for r in cur.fetchall()}


def mask_row(cur, resolver, table, key_cols, col_rules, cols_list, row, key_str,
             dry_run, stats, entity_filter=None):
    """Mask one row. Returns number of columns changed."""
    if entity_filter is not None:
        # entity-scoped masking: resolve the owning corp type and skip outsiders
        entity_type, _corp = resolver.resolve(table, cols_list, row)
        if entity_type is None or entity_type not in entity_filter:
            stats['skipped'] += 1
            return 0
    changed = 0
    for col, rule in col_rules.items():
        if col not in cols_list:
            continue
        orig = row[cols_list.index(col)]
        if orig is None or str(orig).strip() == '':
            continue  # only mask what exists
        orig_text = str(orig).strip()
        masked = masked_value_for(rule, col, key_str)
        if masked is None:
            # pool has no value for this part (e.g. addr_line_2) -> write SQL NULL
            changed += 1
            stats['changed'] += 1
            if not dry_run:
                cur.execute("UPDATE {} SET {} = NULL WHERE {}".format(
                    table, col, ' AND '.join('{} = %s'.format(k) for k in key_cols)),
                    list(row[cols_list.index(k)] for k in key_cols))
            continue
        if orig_text == masked:
            continue  # masked value equals original (e.g. province BC): nothing to do
        # reuse an existing mapping if present
        cur.execute(
            "SELECT masked_value FROM mig_masking_map "
            "WHERE source_table=%s AND source_key=%s AND column_name=%s",
            (table, key_str, col))
        hit = cur.fetchone()
        if hit:
            masked = hit[0]
            stats['map_reused'] += 1
            if str(orig).strip() == str(masked):
                continue  # already applied by a previous run
        else:
            entity_type, corp_num = resolver.resolve(table, cols_list, row)
            if not dry_run:
                cur.execute(
                    "INSERT INTO mig_masking_map "
                    "(source_table, source_key, column_name, original_value, masked_value, "
                    " entity_type, corp_num) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (table, key_str, col, orig_text, str(masked),
                     entity_type, corp_num))
                stats['map_new'] += 1
        changed += 1
        stats['changed'] += 1
        if not dry_run:
            cur.execute("UPDATE {} SET {} = %s WHERE {}".format(
                table, col, ' AND '.join('{} = %s'.format(k) for k in key_cols)),
                [masked] + list(row[cols_list.index(k)] for k in key_cols))
    return changed


def main():
    dry_run = '--dry-run' in sys.argv

    env = {}
    for line in open('.env'):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip('"\'')

    dbname = env['DATABASE_NAME_COLIN_MIGR']

    # gate 1: target DB must be in the ALLOWED_MASKING_DB allowlist
    allowed_dbs = [x.strip() for x in env.get('ALLOWED_MASKING_DB', '').split(',')
                   if x.strip()]
    if not allowed_dbs:
        allowed_dbs = list(DEFAULT_ALLOWED_DBS)
        print('note: ALLOWED_MASKING_DB not set in .env, defaulting to {}'.format(
            allowed_dbs))
    if dbname not in allowed_dbs:
        print('REFUSING TO RUN: target db {!r} is not in ALLOWED_MASKING_DB {}.'
              '\n(never run masking against prod or any other database)'
              .format(dbname, allowed_dbs))
        sys.exit(1)

    # gate 2: entity scope. Empty = whole staging DB; otherwise corp-type filter.
    entity_filter = [x.strip().upper() for x in
                     env.get('ALLOWED_ENTITIES_TO_MASK', '').split(',') if x.strip()]

    scope = 'ALL entity types (whole staging DB)' if not entity_filter \
        else ', '.join(entity_filter)
    mode = 'DRY-RUN (no writes)' if dry_run else 'LIVE - values will be overwritten'
    print('=' * 70)
    print('MIGRATION DATA MASKING (ticket #34942)')
    print('  target database : {}'.format(dbname))
    print('  entity scope    : {}'.format(scope))
    print('  mode            : {}'.format(mode))
    print('  masks           : individual names (Faker), emails, phones, addresses')
    print('  never masks     : business names, NULL/empty fields')
    print('=' * 70)
    if not dry_run:
        ans = input('Proceed with masking? (yes/no): ').strip().lower()
        if ans not in ('y', 'yes'):
            print('aborted - nothing was modified')
            sys.exit(0)

    conn = psycopg2.connect(
        host=env['DATABASE_HOST_COLIN_MIGR'], port=env['DATABASE_PORT_COLIN_MIGR'],
        dbname=dbname, user=env['DATABASE_USERNAME_COLIN_MIGR'],
        password=env['DATABASE_PASSWORD_COLIN_MIGR'])
    cur = conn.cursor()

    ensure_map_table(cur)
    conn.commit()
    resolver = OwnerResolver(cur)

    stats = {'rows': 0, 'changed': 0, 'map_reused': 0, 'map_new': 0, 'skipped': 0}
    for table, (key_cols, col_rules) in RULES.items():
        actual_cols = table_columns(cur, table)
        if not actual_cols:
            print('  {:<22} table missing, skipped'.format(table))
            continue
        applicable = {c: r for c, r in col_rules.items() if c in actual_cols}
        if not applicable:
            print('  {:<22} no maskable columns present, skipped'.format(table))
            continue
        cur.execute("SELECT COUNT(*) FROM {}".format(table))
        n = cur.fetchone()[0]
        if n == 0:
            print('  {:<22} 0 rows, nothing to do'.format(table))
            continue

        cur.execute("SELECT {} FROM {}".format(', '.join(actual_cols), table))
        cols_list = [d[0] for d in cur.description]
        rows = cur.fetchall()
        changed = 0
        for row in rows:
            key_str = ':'.join(str(row[cols_list.index(k)]) for k in key_cols)
            before = changed
            changed += mask_row(cur, resolver, table, key_cols, applicable,
                                cols_list, row, key_str, dry_run, stats,
                                entity_filter=entity_filter or None)
            if changed > before:
                stats['rows'] += 1
        if dry_run:
            conn.rollback()
        else:
            conn.commit()
        print('  {:<22} {} rows, {} column values masked'.format(table, n, changed))

    print()
    print('summary: {} rows touched, {} column values updated, '
          '{} map entries reused, {} new, {} rows skipped by entity filter'.format(
              stats['rows'], stats['changed'], stats['map_reused'],
              stats['map_new'], stats['skipped']))
    if dry_run:
        print('dry-run: no changes written, no map entries created')
    else:
        cur.execute("SELECT COUNT(*) FROM mig_masking_map")
        print('mig_masking_map now has {} entries'.format(cur.fetchone()[0]))
    conn.close()


if __name__ == '__main__':
    main()
