"""add_columns_to_furnishings

Revision ID: feb206b2ce65
Revises: ac0065d92893
Create Date: 2024-07-10 17:33:24.126671

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'feb206b2ce65'
down_revision = 'ac0065d92893'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('furnishings', sa.Column('last_ar_date', sa.DateTime(timezone=True), autoincrement=False, nullable=True))
    op.add_column('furnishings', sa.Column('business_name', sa.String(length=1000), autoincrement=False, nullable=True))


def downgrade():
    op.drop_column('furnishings', 'last_ar_date')
    op.drop_column('furnishings', 'business_name')
