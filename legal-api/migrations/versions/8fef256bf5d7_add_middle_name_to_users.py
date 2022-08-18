"""add_middle_name_to_users

Revision ID: 8fef256bf5d7
Revises: ee956cbf198a
Create Date: 2022-08-18 11:59:34.054976

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8fef256bf5d7'
down_revision = 'ee956cbf198a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('middlename', sa.String(length=1000), nullable=True))
    op.add_column('users_version', sa.Column('middlename', sa.String(length=1000), nullable=True))


def downgrade():
    op.drop_column('users_version', 'middlename')
    op.drop_column('users', 'middlename')
