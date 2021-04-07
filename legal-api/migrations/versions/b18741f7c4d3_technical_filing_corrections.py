"""technical-filing-corrections

Revision ID: b18741f7c4d3
Revises: 2dedf50a17ef
Create Date: 2021-03-22 14:53:58.551918

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b18741f7c4d3'
down_revision = '2dedf50a17ef'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('filings', sa.Column('tech_correction_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade():
    op.drop_column('filings', 'tech_correction_json')
