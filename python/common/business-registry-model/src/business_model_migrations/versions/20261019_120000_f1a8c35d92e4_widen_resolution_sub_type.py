"""widen resolution sub_type to 30 characters so amalgamationApplication fits

Revision ID: f1a8c35d92e4
Revises: 78ce7f82c239
Create Date: 2026-10-19 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'f1a8c35d92e4'
down_revision = '78ce7f82c239'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('resolutions', schema=None) as batch_op:
        batch_op.alter_column(
            'sub_type',
            type_=sa.String(length=30),
            existing_type=sa.String(length=20),
            existing_nullable=True)

    with op.batch_alter_table('resolutions_version', schema=None) as batch_op:
        batch_op.alter_column(
            'sub_type',
            type_=sa.String(length=30),
            existing_type=sa.String(length=20),
            existing_nullable=True)


def downgrade():
    with op.batch_alter_table('resolutions_version', schema=None) as batch_op:
        batch_op.alter_column(
            'sub_type',
            type_=sa.String(length=20),
            existing_type=sa.String(length=30),
            existing_nullable=True)

    with op.batch_alter_table('resolutions', schema=None) as batch_op:
        batch_op.alter_column(
            'sub_type',
            type_=sa.String(length=20),
            existing_type=sa.String(length=30),
            existing_nullable=True)
