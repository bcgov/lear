"""update_dc_connections_table

Revision ID: e6a6e9e25fb9
Revises: 0dc8127c32d9
Create Date: 2025-03-15 21:56:11.895597

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e6a6e9e25fb9'
down_revision = '0dc8127c32d9'
branch_labels = None
depends_on = None


def upgrade():
    # Add a column business_user_id to the dc_connections table that is a foreign key to the dc_business_users table
    op.add_column('dc_connections', sa.Column('business_user_id',
                  sa.Integer, sa.ForeignKey('dc_business_users.id')))
    # Populate the business_user_id in dc_connections from the dc_business_users table, joining on business_id
    op.execute("UPDATE dc_connections \
        SET business_user_id = ( \
            SELECT bu.id \
            FROM dc_business_users bu \
            WHERE dc_connections.business_id = bu.business_id \
        )")


def downgrade():
    # Drop the business_user_id column from the dc_connections table
    op.drop_column('dc_connections', 'business_user_id')
