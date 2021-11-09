""" add last_coa_cod filing dates

Revision ID: b6997f07700a
Revises: 9c95a9b28eb3
Create Date: 2021-08-18 18:43:40.911509

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b6997f07700a'
down_revision = '9c95a9b28eb3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('businesses', sa.Column('last_coa_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('businesses', sa.Column('last_cod_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('businesses_version', sa.Column('last_coa_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('businesses_version', sa.Column('last_cod_date', sa.DateTime(timezone=True), nullable=True))

def downgrade():
    op.drop_column('businesses', 'last_cod_date')
    op.drop_column('businesses', 'last_coa_date')
    op.drop_column('businesses_version', 'last_cod_date')
    op.drop_column('businesses_version', 'last_coa_date')
