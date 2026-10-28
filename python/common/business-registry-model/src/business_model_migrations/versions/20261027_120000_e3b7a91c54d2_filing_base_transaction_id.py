"""filing_base_transaction_id

Revision ID: e3b7a91c54d2
Revises: f1a8c35d92e4
Create Date: 2026-10-27 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'e3b7a91c54d2'
down_revision = 'f1a8c35d92e4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('filings', sa.Column('base_transaction_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        'filings_base_transaction_id_fkey', 'filings', 'transaction', ['base_transaction_id'], ['id']
    )


def downgrade():
    op.drop_constraint('filings_base_transaction_id_fkey', 'filings', type_='foreignkey')
    op.drop_column('filings', 'base_transaction_id')
