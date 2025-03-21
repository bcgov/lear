"""update_dc_credentials_table_columns

Revision ID: edb19fafc835
Revises: e6a6e9e25fb9
Create Date: 2025-03-15 23:42:52.587073

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'edb19fafc835'
down_revision = 'e6a6e9e25fb9'
branch_labels = None
depends_on = None


def upgrade():
    # Rename the columns in the dc_issued_credentials table
    op.alter_column('dc_issued_credentials', 'dc_definition_id',
                    new_column_name='definition_id')
    op.alter_column('dc_issued_credentials', 'dc_connection_id',
                    new_column_name='connection_id')


def downgrade():
    # Reverse the column renames in the dc_issued_credentials table
    op.alter_column('dc_issued_credentials', 'definition_id',
                    new_column_name='dc_definition_id')
    op.alter_column('dc_issued_credentials', 'connection_id',
                    new_column_name='dc_connection_id')
