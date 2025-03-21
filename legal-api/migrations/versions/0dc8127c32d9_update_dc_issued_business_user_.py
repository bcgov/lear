"""update_dc_issued_business_user_credentials_table

Revision ID: 0dc8127c32d9
Revises: 201e34168903
Create Date: 2025-03-15 20:59:54.812748

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0dc8127c32d9'
down_revision = '201e34168903'
branch_labels = None
depends_on = None


def upgrade():
    # Rename the table from dc_issued_business_user_credentials to dc_business_users
    op.rename_table('dc_issued_business_user_credentials', 'dc_business_users')

    # Add unique constraint on business_id and user_id
    op.create_unique_constraint(
        'dc_business_users_business_id_user_id_uq', 'dc_business_users', ['business_id', 'user_id'])


def downgrade():
    # Remove the unique constraint
    op.drop_constraint('dc_business_users_business_id_user_id_uq',
                       'dc_business_users', type_='unique')

    # Rename the table back to its original name
    op.rename_table('dc_business_users', 'dc_issued_business_user_credentials')
