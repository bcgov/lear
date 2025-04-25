"""add_liquidation_office_to_office_types

Revision ID: 1ec937c2466e
Revises: edb19fafc835
Create Date: 2025-04-24 18:34:36.583590

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '1ec937c2466e'
down_revision = 'edb19fafc835'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""insert into office_types (identifier, description) values('liquidationRecordsOffice', 'Liquidation Records Office')""")


def downgrade():
    op.execute("""delete from office_types where identifier = 'liquidationRecordsOffice'""")
