"""add_trigger_date_to_batch_processing

Revision ID: 3083d361616e
Revises: c4732cd8abfd
Create Date: 2024-06-07 12:28:42.308094

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3083d361616e'
down_revision = 'c4732cd8abfd'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('batch_processing', sa.Column('trigger_date', sa.TIMESTAMP(timezone=True), nullable=True))


def downgrade():
    op.drop_column('batch_processing', 'trigger_date')
