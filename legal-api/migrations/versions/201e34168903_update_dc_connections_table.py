"""update_dc_connections_table

Revision ID: 201e34168903
Revises: 0dc8127c32d9
Create Date: 2025-02-27 00:52:44.233035

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '201e34168903'
down_revision = '0dc8127c32d9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('dc_connections', sa.Column(
        'is_attested',  sa.Boolean, default=False))
    op.add_column('dc_connections', sa.Column(
        'last_attested', sa.DateTime, default=None))
    op.execute(
        'UPDATE dc_connections SET connection_state = \'invitation-sent\' WHERE connection_state = \'invitation\'')
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
    op.execute(
        'UPDATE dc_connections SET connection_state = \'invitation\' WHERE connection_state = \'invitation-sent\'')
    op.drop_column('dc_connections', 'is_attested')
    op.drop_column('dc_connections', 'last_attested')
