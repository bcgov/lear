"""accession_number

Revision ID: dbf687803623
Revises: 9fa0f4fde9755
Create Date: 2025-06-26 17:50:36.990739

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'dbf687803623'
down_revision = '9fa0f4fde9755'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('businesses', sa.Column(
        'accession_number', sa.String(length=10), nullable=True))
    op.add_column('businesses_version', sa.Column(
        'accession_number', sa.String(length=10), nullable=True))


def downgrade():
    op.drop_column('businesses_version', 'accession_number')
    op.drop_column('businesses', 'accession_number')
