"""colin amalgamating business

Revision ID: a3c9e1f04b27
Revises: d7fc1a767d69
Create Date: 2026-08-24 10:15:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'a3c9e1f04b27'
down_revision = 'd7fc1a767d69'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('amalgamating_businesses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('colin_identifier', sa.String(length=10), nullable=True))

    with op.batch_alter_table('amalgamating_businesses_version', schema=None) as batch_op:
        batch_op.add_column(sa.Column('colin_identifier', sa.String(length=10), nullable=True))


def downgrade():
    with op.batch_alter_table('amalgamating_businesses_version', schema=None) as batch_op:
        batch_op.drop_column('colin_identifier')

    with op.batch_alter_table('amalgamating_businesses', schema=None) as batch_op:
        batch_op.drop_column('colin_identifier')
