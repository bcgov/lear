"""index-by-idp-guid

Revision ID: bddd732a9269
Revises: 5ee13998918d
Create Date: 2022-12-13 09:20:50.961105

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bddd732a9269'
down_revision = '5ee13998918d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(op.f('ix_user_idp_userid'), 'users', ['idp_userid'], unique=True)
    op.create_unique_constraint('users_idp_userid_key', 'users', ['idp_userid'])


def downgrade():
    op.drop_index(op.f('ix_user_idp_userid'), table_name='users')
    op.drop_constraint('users_idp_userid_key', 'users', ['idp_userid'])
