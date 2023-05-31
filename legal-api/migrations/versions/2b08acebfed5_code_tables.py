"""code_tables

Revision ID: 2b08acebfed5
Revises: e9e05a998ea9
Create Date: 2023-05-31 09:23:48.784274

"""
from alembic import op
from sqlalchemy.sql import table, column
from sqlalchemy import String


# revision identifiers, used by Alembic.
revision = '2b08acebfed5'
down_revision = 'e9e05a998ea9'
branch_labels = None
depends_on = None


def upgrade():

    office_types_table = table('office_types',
        column('identifier', String),
        column('description', String),
    )

    op.bulk_insert(
        office_types_table,
        [
            {
                'identifier':'registeredOffice', 'description':'Registered Office'
            },
            {
                'identifier':'recordsOffice', 'description':'Records Office'
            },
            {
                'identifier':'custodialOffice', 'description':'Custodial Office'
            },
            {
                'identifier':'businessOffice', 'description':'Business Office'
            },
        ]
    )

def downgrade():
    pass
