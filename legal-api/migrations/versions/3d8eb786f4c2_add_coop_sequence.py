"""add_coop_sequence

Revision ID: 3d8eb786f4c2
Revises: b6997f07700a
Create Date: 2021-10-24 14:45:58.533628

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3d8eb786f4c2'
down_revision = 'b6997f07700a'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE SEQUENCE business_identifier_coop START 1002395")


def downgrade():
    op.execute("DROP SEQUENCE business_identifier_coop")
