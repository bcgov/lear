"""add order_details column

Revision ID: 1fcdb213657d
Revises: 78ddb7f6f8b5
Create Date: 2021-05-27 13:29:27.893982

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1fcdb213657d'
down_revision = '78ddb7f6f8b5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('filings', sa.Column('order_details', sa.String(length=2000), nullable=True))


def downgrade():
    op.drop_column('filings', 'order_details')
