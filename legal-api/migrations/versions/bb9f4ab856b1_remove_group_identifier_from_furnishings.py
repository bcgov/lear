"""remove_group_identifier_from_furnishings

Revision ID: bb9f4ab856b1
Revises: b14f77400786
Create Date: 2024-07-25 15:21:31.652920

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bb9f4ab856b1'
down_revision = 'b14f77400786'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('furnishings','grouping_identifier')
    op.execute("DROP SEQUENCE grouping_identifier;")
    pass


def downgrade():
    op.add_column('furnishings', sa.Column('grouping_identifier', sa.Integer(), nullable=True))
    op.execute("CREATE SEQUENCE grouping_identifier START 1;")
    pass
