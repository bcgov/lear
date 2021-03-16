"""added court order columns to filings table

Revision ID: 2dedf50a17ef
Revises: 11a256335c79
Create Date: 2021-03-16 09:22:26.320011

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2dedf50a17ef'
down_revision = '11a256335c79'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('filings', sa.Column('court_order_file_number', sa.String(length=20), nullable=True))
    op.add_column('filings', sa.Column('court_order_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('filings', sa.Column('court_order_effect_of_order', sa.String(length=500), nullable=True))


def downgrade():
    pass
