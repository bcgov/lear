"""Add custodialOffice to office_types

Revision ID: 026f42f4f654
Revises: 3d8eb786f4c2
Create Date: 2021-11-29 09:58:45.953911

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '026f42f4f654'
down_revision = '3d8eb786f4c2'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('insert into office_types (identifier, description) values(\'custodialOffice\', \'Custodial Office\')')


def downgrade():
    op.execute('delete from office_types where identifier = \'custodialOffice\'')
