"""create shadow_business, shadow_filing, and legacy_outputs tables

Revision ID: 3cad4247b576
Revises: 08da65c4a94a
Create Date: 2023-03-30 16:04:24.255002

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3cad4247b576'
down_revision = '08da65c4a94a'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('shadow_filings', 
        sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('filing_date', sa.DateTime(timezone=True)),
        sa.Column('filing_type', sa.String(30)),
        sa.Column('filing_sub_type', sa.String(30)),
        sa.Column('filing_json', sa.JSON),
        sa.Column('meta_data', sa.JSON),
        sa.Column('status', sa.String(20), default='DRAFT'),
        sa.Column('source', sa.String(15), default='LEAR'),
        sa.Column('business_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('effective_date', sa.DateTime(timezone=True), autoincrement=False, nullable=True),
        sa.Column('has_legacy_outputs', sa.Boolean(), nullable=True),
        sa.Column('colin_event_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id']),
        sa.ForeignKeyConstraint(['colin_event_id'], ['colin_event_id.colin_event_id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('shadow_businesses', 
        sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('identifier', sa.String(10)),
        sa.Column('legal_type', sa.String(10)),
        sa.Column('legal_name', sa.String(1000), nullable=True),
        sa.Column('founding_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('state', sa.Enum),
        sa.Column('state_filing_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['state_filing_id'], ['filing.id']), # not entirely sure this is the right relationship
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_shadow_business_identifier'), 'shadow_businesses', ['identifier'], unique=False)
    op.create_index(op.f('ix_shadow_business_legal_name'), 'shadow_businesses', ['legal_name'], unique=False)

    op.create_table('legacy_outputs',
        sa.Column('colin_event_id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('legacy_output_id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('filing_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('type', sa.String(30), nullable=True),
        sa.ForeignKeyConstraint(['filing_id'], ['filing.id'])
    )


def downgrade():
    op.drop_table('shadow_filings')
    op.drop_table('shadow_business')
    op.drop_table('shadow_legacy_outputs')
