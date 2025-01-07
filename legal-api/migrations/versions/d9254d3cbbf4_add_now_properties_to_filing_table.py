"""add_NoW_properties_to_filing_table

Revision ID: d9254d3cbbf4
Revises: f99e7bda56bb
Create Date: 2025-01-02 16:52:38.449590

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd9254d3cbbf4'
down_revision = 'f99e7bda56bb'
branch_labels = None
depends_on = None


def upgrade():
     op.add_column('filings', sa.Column('withdrawn_filing_id', sa.Integer(), nullable=True))
     op.create_foreign_key('filings_withdrawn_filing_id_fkey', 'filings', 'filings', ['withdrawn_filing_id'], ['id'])
     op.add_column('filings', sa.Column('withdrawal_pending', sa.Boolean(), nullable=True))

def downgrade():
    op.drop_constraint('filings_withdrawn_filing_id_fkey', 'filings', type_='foreignkey')
    op.drop_column('filings', 'withdrawn_filing_id')
    op.drop_column('filings', 'withdrawal_pending')
