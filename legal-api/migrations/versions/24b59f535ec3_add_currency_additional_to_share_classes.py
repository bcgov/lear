"""add_currency_additional_to_share_classes

Revision ID: 24b59f535ec3
Revises: f1d010259785
Create Date: 2025-02-28 23:28:54.053129

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '24b59f535ec3'
down_revision = 'f1d010259785'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('share_classes', sa.Column('currency_additional', sa.String(length=40)))
    op.add_column('share_classes_version', sa.Column('currency_additional', sa.String(length=40)))


def downgrade():
    op.drop_column('share_classes', 'currency_additional')
    op.drop_column('share_classes_version', 'currency_additional')
