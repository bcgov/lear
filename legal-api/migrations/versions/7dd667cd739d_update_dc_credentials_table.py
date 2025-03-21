"""update_dc_credentials_table

Revision ID: 7dd667cd739d
Revises: a81ac0037e42
Create Date: 2025-03-18 15:23:21.812300

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '7dd667cd739d'
down_revision = 'a81ac0037e42'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('dc_credentials', sa.Column(
        'date_of_revocation', sa.DateTime(timezone=True)))
    op.add_column('dc_credentials', sa.Column('raw_data', JSONB))
    op.add_column('dc_credentials', sa.Column('is_role_self_attested', sa.Boolean))


def downgrade():
    op.drop_column('dc_credentials', 'is_role_self_attested')
    op.drop_column('dc_credentials', 'raw_data')
    op.drop_column('dc_credentials', 'date_of_revocation')
