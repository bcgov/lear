"""xml_payloads

Revision ID: b14f77400786
Revises: feb206b2ce65
Create Date: 2024-07-17 23:46:20.873233

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b14f77400786'
down_revision = 'feb206b2ce65'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('xml_payloads',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('payload', sa.TEXT, nullable=False),    
    sa.Column('created_date', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('furnishing_groups',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('xml_payload_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['xml_payload_id'], ['xml_payloads.id']),
    sa.PrimaryKeyConstraint('id')
    )

    op.add_column('furnishings', sa.Column('furnishing_group_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'furnishings', 'furnishing_groups', ['furnishing_group_id'], ['id'])
    pass


def downgrade():
    op.drop_column('furnishings', 'furnishing_group_id')
    op.drop_table('furnishing_groups')
    op.drop_table('xml_payloads')
    pass
