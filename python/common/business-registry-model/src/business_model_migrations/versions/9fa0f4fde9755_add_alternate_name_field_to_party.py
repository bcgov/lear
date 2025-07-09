"""empty message

Revision ID: fa0f4fde9755
Revises: 8f3a9c12de4b
Create Date: 2025-06-18 18:40:22.151208

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '9fa0f4fde9755'
down_revision = '8f3a9c12de4b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('parties', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('alternate_name', sa.String(length=90), nullable=True))

    with op.batch_alter_table('parties_version', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('alternate_name', sa.String(length=90), nullable=True))


def downgrade():
    with op.batch_alter_table('parties', schema=None) as batch_op:
        batch_op.drop_column('alternate_name')

    with op.batch_alter_table('parties_version', schema=None) as batch_op:
        batch_op.drop_column('alternate_name')
