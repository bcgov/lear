"""update_dc_credentials_table

Revision ID: a81ac0037e42
Revises: 1e327ace7673
Create Date: 2025-03-16 00:47:47.879010

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a81ac0037e42'
down_revision = '1e327ace7673'
branch_labels = None
depends_on = None


def upgrade():
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


def downgrade():
    # Drop the business_user_id column from the dc_credentials table
    op.drop_column('dc_credentials', 'business_user_id')
