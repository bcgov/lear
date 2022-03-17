"""Add businessOffice to office_types

Revision ID: f4f654026f42
Revises: dbe1cfc78599
Create Date: 2022-03-16 12:58:45.953911

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f4f654026f42'
down_revision = 'dbe1cfc78599'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('insert into office_types (identifier, description) values(\'businessOffice\', \'Business Office\')')


def downgrade():
    op.execute('delete from office_types where identifier = \'businessOffice\'')
