"""add indexes for the filings lookups that run as sequential scans in prod

parent_filing_id (children lookup in Filing.json), payment_id (pay queue callback),
colin_event_ids.filing_id (ColinEventId.get_by_filing_id), the COLIN sync paging order,
temp_reg and withdrawn_filing_id. Built CONCURRENTLY so prod keeps serving while they build.
A build that is interrupted (timeout, cancel) leaves an INVALID index behind which IF NOT EXISTS
would then keep, so any invalid copy is dropped before each build. The same index set is
declared on the models so autogenerate does not try to drop them.

Revision ID: a7d3e9f1c2b8
Revises: a9d4c27e81f3
Create Date: 2026-10-27 20:00:00.000000

"""
from contextlib import contextmanager

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'a7d3e9f1c2b8'
down_revision = 'a9d4c27e81f3'
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


@contextmanager
def _outside_transaction():
    """Run DDL that must not be inside a transaction block (CONCURRENTLY).

    alembic's autocommit_block reads the current isolation level through a DBAPI cursor before
    switching the connection to AUTOCOMMIT. On pg8000 (the driver the Cloud Run migration job
    uses) that read opens an implicit transaction which autocommit does not close, so the
    CONCURRENTLY statement still fails with 25001. Ending that block first makes the statements
    run outside any transaction on both pg8000 and psycopg2.
    """
    with op.get_context().autocommit_block():
        op.execute('COMMIT')
        yield


def _drop_if_invalid(name: str):
    """Drop a leftover invalid index so the CONCURRENTLY build below can redo it."""
    invalid = op.get_bind().execute(
        text(
            'SELECT 1 FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid '
            'WHERE c.relname = :name AND NOT i.indisvalid'
        ),
        {'name': name},
    ).scalar()
    if invalid:
        op.execute(f'DROP INDEX CONCURRENTLY IF EXISTS {name}')


def upgrade():
    with _outside_transaction():
        for name, table, column, where in INDEXES:
            _drop_if_invalid(name)
            stmt = f'CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} ON {table} ({column})'
            if where:
                stmt += f' WHERE {where}'
            op.execute(stmt)
        for table in ANALYZE_TABLES:
            op.execute(f'ANALYZE {table}')


def downgrade():
    with _outside_transaction():
        for name, _table, _column, _where in reversed(INDEXES):
            op.execute(f'DROP INDEX CONCURRENTLY IF EXISTS {name}')
