"""empty message

Revision ID: e6ed22dc70ca
Revises: 1215735c3563
Create Date: 2019-07-03 14:25:05.759877

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e6ed22dc70ca'
down_revision = '1215735c3563'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('businesses', sa.Column('last_agm_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('businesses_version', sa.Column('last_agm_date', sa.DateTime(timezone=True), autoincrement=False, nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('businesses_version', 'last_agm_date')
    op.drop_column('businesses', 'last_agm_date')
    # ### end Alembic commands ###