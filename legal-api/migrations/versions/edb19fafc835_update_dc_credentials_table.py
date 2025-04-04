"""update_dc_credentials_table

Revision ID: edb19fafc835
Revises: 201e34168903
Create Date: 2025-03-15 23:42:52.587073

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = 'edb19fafc835'
down_revision = '201e34168903'
branch_labels = None
depends_on = None


def upgrade():
    # Rename dc_issued_credentials table to dc_credentials
    op.rename_table('dc_issued_credentials', 'dc_credentials')
    # Rename the columns in the dc_credentials table
    op.alter_column('dc_credentials', 'dc_definition_id',
                    new_column_name='definition_id')
    op.alter_column('dc_credentials', 'dc_connection_id',
                    new_column_name='connection_id')
    # Add a new column business_user_id to the dc_credentials table
    op.add_column('dc_credentials', sa.Column(
        'business_user_id', sa.Integer, sa.ForeignKey('dc_business_users.id')))
    # Populate the business_user_id column in dc_credentials from the dc_business_users table
    op.execute("UPDATE dc_credentials \
        SET business_user_id = ( \
            SELECT bu.id \
            FROM dc_business_users bu \
            JOIN dc_connections c ON c.id = dc_credentials.connection_id \
            WHERE c.business_id = bu.business_id \
        )")
    op.add_column('dc_credentials', sa.Column(
        'date_of_revocation', sa.DateTime(timezone=True)))
    op.add_column('dc_credentials', sa.Column('raw_data', JSONB))
    op.add_column('dc_credentials', sa.Column('self_attested_roles', JSONB))


def downgrade():
    op.drop_column('dc_credentials', 'self_attested_roles')
    op.drop_column('dc_credentials', 'raw_data')
    op.drop_column('dc_credentials', 'date_of_revocation')
    # Drop the business_user_id column from the dc_credentials table
    op.drop_column('dc_credentials', 'business_user_id')
    # Reverse the column renames in the dc_credentials table
    op.alter_column('dc_credentials', 'definition_id',
                    new_column_name='dc_definition_id')
    op.alter_column('dc_credentials', 'connection_id',
                    new_column_name='dc_connection_id')
    # Rename dc_credentials table back to dc_issued_credentials
    op.rename_table('dc_credentials', 'dc_issued_credentials')
