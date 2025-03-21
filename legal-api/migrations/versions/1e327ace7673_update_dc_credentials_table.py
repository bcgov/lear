"""update_dc_credentials_table

Revision ID: 1e327ace7673
Revises: edb19fafc835
Create Date: 2025-03-16 00:14:51.173454

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1e327ace7673'
down_revision = 'edb19fafc835'
branch_labels = None
depends_on = None


def upgrade():
    # Rename dc_issued_credentials table to dc_credentials
    op.rename_table('dc_issued_credentials', 'dc_credentials')


def downgrade():
    # Rename dc_credentials table back to dc_issued_credentials
    op.rename_table('dc_credentials', 'dc_issued_credentials')
