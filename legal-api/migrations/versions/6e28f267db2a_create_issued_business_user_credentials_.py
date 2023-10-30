"""create issued business user credentials table

Revision ID: 6e28f267db2a
Revises: 8148a25d695e
Create Date: 2023-10-17 02:17:08.232290

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6e28f267db2a'
down_revision = '8148a25d695e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('dc_issued_business_user_credentials',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('business_id', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.ForeignKeyConstraint(['business_id'], ['businesses.id']),
    sa.ForeignKeyConstraint(['user_id'], ['users.id']))


def downgrade():
    op.drop_table('dc_issued_business_user_credentials')
