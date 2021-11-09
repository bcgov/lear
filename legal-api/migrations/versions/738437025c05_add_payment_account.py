"""add_payment_account

Revision ID: 738437025c05
Revises: 5e1faa8636c0
Create Date: 2020-10-22 23:16:16.261553

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '738437025c05'
down_revision = '5e1faa8636c0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('filings', sa.Column('payment_account', sa.String(length=30), nullable=True))


def downgrade():
    op.drop_column('filings', 'payment_account')
