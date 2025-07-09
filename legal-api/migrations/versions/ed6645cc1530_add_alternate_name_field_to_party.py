"""add alternate name field to party

Revision ID: ed6645cc1530
Revises: 99575010ed4b
Create Date: 2025-06-19 00:57:53.223323

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ed6645cc1530'
down_revision = '99575010ed4b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('parties', sa.Column('alternate_name', sa.String(length=90), nullable=True))
    op.add_column('parties_version', sa.Column('alternate_name', sa.String(length=90), autoincrement=False, nullable=True))


def downgrade():
    op.drop_column('parties_version', 'alternate_name')
    op.drop_column('parties', 'alternate_name')
