"""Add SFTP configuration.

Revision ID: a7d3a3aa76de
Revises: 7d486343384b
Create Date: 2024-08-30 13:07:08.377059

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7d3a3aa76de'
down_revision = '7d486343384b'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""INSERT INTO configurations (name, val, short_description, full_description) VALUES
            ('ENABLE_FURNISHINGS_SFTP', 'True', 'Turns SFTP functionality on and off.', 'Turns SFTP functionality on and off.')
            """)


def downgrade():
    op.execute("""DELETE FROM configurations
            WHERE name = 'ENABLE_FURNISHINGS_SFTP'
            """)
