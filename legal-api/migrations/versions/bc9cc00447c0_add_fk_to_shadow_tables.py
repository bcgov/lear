"""add FK to shadow tables

Revision ID: bc9cc00447c0
Revises: 481337b84fb2
Create Date: 2023-04-06 17:33:06.127330

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bc9cc00447c0'
down_revision = '481337b84fb2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('shadow_filings', sa.Column('business_id', sa.Integer(), autoincrement=False, nullable=True))
    op.add_column('shadow_filings', sa.Column('colin_event_id', sa.Integer(), autoincrement=False, nullable=True))
    op.create_foreign_key(None, 'shadow_filings', 'shadow_businesses', ['business_id'], ['id'])
    op.create_foreign_key(None, 'shadow_filings', 'legacy_outputs', ['colin_event_id'], ['colin_event_id'])

    pass


def downgrade():
    pass
