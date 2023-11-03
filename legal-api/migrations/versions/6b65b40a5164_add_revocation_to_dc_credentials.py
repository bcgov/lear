"""add revocation to dc_credentials

Revision ID: 6b65b40a5164
Revises: 9a9ac165365e
Create Date: 2023-10-11 22:20:14.023687

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6b65b40a5164'
down_revision = '9a9ac165365e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('dc_issued_credentials', sa.Column('credential_revocation_id', sa.String(length=10), nullable=True))
    op.add_column('dc_issued_credentials', sa.Column('revocation_registry_id', sa.String(length=200), nullable=True))


def downgrade():
    op.drop_column('dc_issued_credentials', 'credential_revocation_id')
    op.drop_column('dc_issued_credentials', 'revocation_registry_id')
