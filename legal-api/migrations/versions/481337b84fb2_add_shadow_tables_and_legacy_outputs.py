"""add shadow tables and legacy outputs

Revision ID: 481337b84fb2
Revises: 89fe33f436c1
Create Date: 2023-04-06 11:05:38.022157

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '481337b84fb2'
down_revision = '89fe33f436c1'
branch_labels = None
depends_on = None


def upgrade():

    op.create_table('shadow_filings', 
                    sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
                    sa.Column('filing_date', sa.DateTime(timezone=True), autoincrement=False, nullable=True),
                    sa.Column('filing_type', sa.String(length=30), autoincrement=False, nullable=True),
                    sa.Column('filing_sub_type', sa.String(length=30), autoincrement=False, nullable=True),
                    sa.Column('filing_json', sa.JSON(), autoincrement=False, nullable=True),
                    sa.Column('meta_data', sa.JSON(), autoincrement=False, nullable=True),
                    sa.Column('status', sa.String(length=20), default='DRAFT', autoincrement=False, nullable=True),
                    sa.Column('source', sa.String(length=15), default='LEAR', autoincrement=False, nullable=True),
                    sa.Column('effective_date', sa.DateTime(timezone=True), autoincrement=False, nullable=True),
                    sa.Column('has_legacy_outputs', sa.Boolean(), autoincrement=False, nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    
    op.create_table('shadow_businesses', 
        sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('identifier', sa.String(length=10), autoincrement=False, nullable=True),
        sa.Column('legal_type', sa.String(length=10), autoincrement=False, nullable=True),
        sa.Column('legal_name', sa.String(length=1000), autoincrement=False, nullable=True),
        sa.Column('founding_date', sa.DateTime(timezone=True), autoincrement=False, nullable=True),
        sa.Column('state', sa.String(length=30), autoincrement=False, nullable=True),
        sa.Column('state_filing_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['state_filing_id'], ['shadow_filings.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_shadow_business_identifier'), 'shadow_businesses', ['identifier'], unique=False)
    op.create_index(op.f('ix_shadow_business_legal_name'), 'shadow_businesses', ['legal_name'], unique=False)

    op.create_table('legacy_outputs',
        sa.Column('colin_event_id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('legacy_output_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('filing_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('type', sa.String(length=30), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['filing_id'], ['shadow_filings.id']),
        sa.PrimaryKeyConstraint('colin_event_id')
    )




def downgrade():
    # op.drop_index(op.f('ix_shadow_business_identifier'), table_name='shadow_businesses')
    # op.drop_index(op.f('ix_shadow_business_legal_name'), table_name='shadow_businesses')
    op.drop_table('shadow_filings')
    # op.drop_table('shadow_businesses')
    # op.drop_table('legacy_outputs')

