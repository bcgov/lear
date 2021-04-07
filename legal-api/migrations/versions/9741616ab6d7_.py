"""empty message

Revision ID: 9741616ab6d7
Revises: 2dedf50a17ef
Create Date: 2021-04-07 12:11:43.539782

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9741616ab6d7'
down_revision = '2dedf50a17ef'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('filings', sa.Column('colin_only', sa.Boolean(), nullable=True))
    

def downgrade():
    op.drop_column('filings', 'colin_only')
