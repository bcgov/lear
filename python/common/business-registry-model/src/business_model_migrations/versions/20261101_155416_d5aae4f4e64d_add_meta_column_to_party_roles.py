"""add_meta_column_to_party_roles

Revision ID: d5aae4f4e64d
Revises: b8e4f0a2d3c9
Create Date: 2026-11-01 15:54:16.938860

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd5aae4f4e64d'
down_revision = 'b8e4f0a2d3c9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'party_roles',
        sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    op.add_column(
        'party_roles_version',
        sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True)
    )


def downgrade():
    op.drop_column('party_roles_version', 'meta')
    op.drop_column('party_roles', 'meta')