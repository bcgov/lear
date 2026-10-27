"""drop duplicate indexes left behind on businesses and colin_event_ids

Prod carries _ccold / _ccold1 copies of every businesses index (leftovers of REINDEX
CONCURRENTLY) and a UNIQUE constraint on colin_event_ids.colin_event_id that duplicates the
primary key. All are valid duplicates with no constraint of their own, so every write
maintains three btrees where one is needed. IF EXISTS keeps this a no-op on environments
that never had them.

Revision ID: b8e4f0a2d3c9
Revises: a7d3e9f1c2b8
Create Date: 2026-10-27 20:15:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b8e4f0a2d3c9'
down_revision = 'a7d3e9f1c2b8'
branch_labels = None
depends_on = None


DUPLICATE_INDEXES = [
    'businesses_pkey_ccold',
    'businesses_pkey_ccold1',
    'ix_businesses_identifier_ccold',
    'ix_businesses_identifier_ccold1',
    'ix_businesses_legal_name_ccold',
    'ix_businesses_legal_name_ccold1',
    'ix_businesses_tax_id_ccold',
    'ix_businesses_tax_id_ccold1',
]


def upgrade():
    with op.get_context().autocommit_block():
        for name in DUPLICATE_INDEXES:
            op.execute(f'DROP INDEX CONCURRENTLY IF EXISTS {name}')
    op.execute('ALTER TABLE colin_event_ids DROP CONSTRAINT IF EXISTS colin_event_ids_colin_event_id_key')


def downgrade():
    # the _ccold copies were never meant to exist; only the unique constraint is restored
    op.execute(
        'ALTER TABLE colin_event_ids '
        'ADD CONSTRAINT colin_event_ids_colin_event_id_key UNIQUE (colin_event_id)'
    )
