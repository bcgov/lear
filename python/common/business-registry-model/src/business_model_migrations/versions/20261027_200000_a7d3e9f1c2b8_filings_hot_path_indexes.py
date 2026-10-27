"""add indexes for the filings lookups that run as sequential scans in prod

parent_filing_id (children lookup in Filing.json), payment_id (pay queue callback),
colin_event_ids.filing_id (ColinEventId.get_by_filing_id), the COLIN sync paging order,
temp_reg and withdrawn_filing_id. Built CONCURRENTLY so prod keeps serving while they build.

Revision ID: a7d3e9f1c2b8
Revises: f1a8c35d92e4
Create Date: 2026-10-27 20:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'a7d3e9f1c2b8'
down_revision = 'f1a8c35d92e4'
branch_labels = None
depends_on = None


INDEXES = [
    ('ix_filings_parent_filing_id', 'filings', 'parent_filing_id',
     'parent_filing_id IS NOT NULL'),
    ('ix_filings_payment_id', 'filings', 'payment_id',
     'payment_id IS NOT NULL'),
    ('ix_colin_event_ids_filing_id', 'colin_event_ids', 'filing_id', None),
    ('ix_filings_colin_sync', 'filings', 'transaction_id',
     "status = 'COMPLETED' AND source = 'LEAR'"),
    ('ix_filings_temp_reg', 'filings', 'temp_reg',
     'temp_reg IS NOT NULL'),
    ('ix_filings_withdrawn_filing_id', 'filings', 'withdrawn_filing_id',
     'withdrawn_filing_id IS NOT NULL'),
]

ANALYZE_TABLES = ['filings', 'colin_event_ids', 'businesses']


def upgrade():
    # CREATE INDEX CONCURRENTLY cannot run inside a transaction block.
    with op.get_context().autocommit_block():
        for name, table, column, where in INDEXES:
            stmt = f'CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} ON {table} ({column})'
            if where:
                stmt += f' WHERE {where}'
            op.execute(stmt)
        for table in ANALYZE_TABLES:
            op.execute(f'ANALYZE {table}')


def downgrade():
    with op.get_context().autocommit_block():
        for name, _table, _column, _where in reversed(INDEXES):
            op.execute(f'DROP INDEX CONCURRENTLY IF EXISTS {name}')
