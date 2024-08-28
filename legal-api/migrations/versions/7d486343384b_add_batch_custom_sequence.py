"""add_batch_custom_sequence

Revision ID: 7d486343384b
Revises: 12f725915617
Create Date: 2024-08-27 18:28:38.962901

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7d486343384b'
down_revision = '12f725915617'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE SEQUENCE batch_custom_identifier START 100000")


def downgrade():
    op.execute("DROP SEQUENCE batch_custom_identifier")
