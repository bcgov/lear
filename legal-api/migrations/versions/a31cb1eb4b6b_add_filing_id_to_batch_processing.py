"""add filing_id_to_batch_processing

Revision ID: a31cb1eb4b6b
Revises: bb9f4ab856b1
Create Date: 2024-08-07 16:54:43.985248

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a31cb1eb4b6b'
down_revision = 'bb9f4ab856b1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('batch_processing', sa.Column('filing_id', sa.Integer(), nullable=True))
    op.create_foreign_key('batch_processing_filing_id_fkey', 'batch_processing', 'filings', ['filing_id'], ['id'])
    pass


def downgrade():
    op.drop_constraint('batch_processing_filing_id_fkey', 'batch_processing', type_='foreignkey')
    op.drop_column('batch_processing', 'filing_id')
    pass
