"""submitter_roles

Revision ID: d21f6be7bd21
Revises: 1fcdb213657d
Create Date: 2021-05-30 13:11:26.955954

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd21f6be7bd21'
# down_revision = '1fcdb213657d'
down_revision = '8c74427a6c0e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('filings', sa.Column('submitter_roles', sa.String(length=200), nullable=True))


def downgrade():
    op.drop_column('filings', 'submitter_roles')