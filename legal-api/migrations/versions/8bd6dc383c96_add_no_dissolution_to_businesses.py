"""add_no_dissolution_to_businesses

Revision ID: 8bd6dc383c96
Revises: 9fc8fcdc0a22
Create Date: 2024-05-06 15:44:52.727065

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8bd6dc383c96'
down_revision = '9fc8fcdc0a22'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('businesses', sa.Column('no_dissolution', sa.Boolean(), autoincrement=False, server_default='False'))
    op.add_column('businesses_version', sa.Column('no_dissolution', sa.Boolean(), autoincrement=False, server_default='False'))


def downgrade():
    op.drop_column('businesses', 'no_dissolution')
    op.drop_column('businesses_version', 'no_dissolution')
