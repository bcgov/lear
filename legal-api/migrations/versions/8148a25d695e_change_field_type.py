"""change field type

Revision ID: 8148a25d695e
Revises: 6b65b40a5164
Create Date: 2023-10-17 01:05:30.977475

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8148a25d695e'
down_revision = '6b65b40a5164'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('dc_issued_credentials', 'credential_id',
        existing_type=sa.String(length=100),
        type_=sa.String(length=10))


def downgrade():
    op.alter_column('dc_issued_credentials', 'credential_id',
        existing_type=sa.String(length=10),
        type_=sa.String(length=100))
