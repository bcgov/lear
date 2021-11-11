"""empty message

Revision ID: 54a3fc54a2cf
Revises: 442829649a2a
Create Date: 2020-05-05 07:49:31.147648

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '54a3fc54a2cf'
down_revision = '442829649a2a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('filings', sa.Column('payment_error_type', sa.String(length=50), nullable=True))


def downgrade():
    op.drop_column('filings', 'payment_error_type')
