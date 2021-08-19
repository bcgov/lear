"""adding filing.meta_data

Revision ID: 9c95a9b28eb3
Revises: d21f6be7bd21
Create Date: 2021-08-18 17:02:24.290127

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9c95a9b28eb3'
down_revision = 'd21f6be7bd21'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('filings', sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade():
    op.drop_column('filings', 'meta_data')
