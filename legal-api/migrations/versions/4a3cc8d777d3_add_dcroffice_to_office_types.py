"""Add dcrOffice to office_types

Revision ID: 4a3cc8d777d3
Revises: edb19fafc835
Create Date: 2025-04-24 14:59:50.394995

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4a3cc8d777d3'
down_revision = 'edb19fafc835'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('insert into office_types (identifier, description) values(\'dcrOffice\', \'Dissolved Company\'\'s Records Office\')')


def downgrade():
    op.execute('delete from office_types where identifier = \'dcrOffice\'')
