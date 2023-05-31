"""corp_sequences

Revision ID: c6d5832b71ea
Revises: bffab2daa2c1
Create Date: 2023-05-31 13:29:16.443251

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c6d5832b71ea'
down_revision = 'bffab2daa2c1'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE SEQUENCE business_identifier_coop START 1002395")


def downgrade():
    op.execute("DROP SEQUENCE business_identifier_coop")
