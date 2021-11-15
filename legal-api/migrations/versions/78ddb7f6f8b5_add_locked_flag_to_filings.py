"""Add deletion_locked flag to filings table

Revision ID: 78ddb7f6f8b5
Revises: 9741616ab6d7
Create Date: 2021-04-16 15:32:15.209352

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '78ddb7f6f8b5'
down_revision = '9741616ab6d7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('filings', sa.Column('deletion_locked', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('filings', 'deletion_locked')
