"""widen party first name to 60 characters

Revision ID: c4e7b2a95d18
Revises: a3c9e1f04b27
Create Date: 2026-09-28 09:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c4e7b2a95d18'
down_revision = 'a3c9e1f04b27'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('parties', schema=None) as batch_op:
        batch_op.alter_column(
            'first_name',
            type_=sa.String(length=60),
            existing_type=sa.String(length=30),
            existing_nullable=True)

    with op.batch_alter_table('parties_version', schema=None) as batch_op:
        batch_op.alter_column(
            'first_name',
            type_=sa.String(length=60),
            existing_type=sa.String(length=30),
            existing_nullable=True)


def downgrade():
    with op.batch_alter_table('parties_version', schema=None) as batch_op:
        batch_op.alter_column(
            'first_name',
            type_=sa.String(length=30),
            existing_type=sa.String(length=60),
            existing_nullable=True)

    with op.batch_alter_table('parties', schema=None) as batch_op:
        batch_op.alter_column(
            'first_name',
            type_=sa.String(length=30),
            existing_type=sa.String(length=60),
            existing_nullable=True)
