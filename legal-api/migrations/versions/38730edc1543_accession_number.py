"""accession_number

Revision ID: 38730edc1543
Revises: ed6645cc1530
Create Date: 2025-06-26 10:21:52.063843

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '38730edc1543'
down_revision = 'ed6645cc1530'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('businesses', sa.Column('accession_number', sa.String(length=10), nullable=True))
    op.add_column('businesses_version', sa.Column('accession_number', sa.String(length=10), nullable=True))


def downgrade():
    op.drop_column('businesses_version', 'accession_number')
    op.drop_column('businesses', 'accession_number')
