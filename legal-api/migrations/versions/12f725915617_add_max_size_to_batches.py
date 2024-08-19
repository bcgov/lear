"""add_max_size_to_batches

Revision ID: 12f725915617
Revises: 01dc3337e726
Create Date: 2024-08-15 10:49:33.155500

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '12f725915617'
down_revision = '01dc3337e726'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('batches', sa.Column('max_size', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('batches', 'max_size')
