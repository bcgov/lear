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
        sa.Column('business_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('submitter_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('effective_date', sa.DateTime(timezone=True), autoincrement=False, nullable=True),
        sa.Column('has_legacy_outputs', sa.Boolean(), nullable=True),
        sa.Column('temp_reg', sa.String(10), nullable=True),
        sa.Column('colin_event_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ),
        sa.ForeignKeyConstraint(['temp_reg'], ['registration_bootstrap.identifier'],),
        sa.ForeignKeyConstraint(['submitter_id'], ['users.id']),
        sa.ForeignKeyConstraint(['colin_event_id'], ['colin_event_id.colin_event_id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('shadow_business', 
        sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('last_ledger_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('last_remote_ledger_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('last_ledger_timestamp', sa.DateTime(timezone=True), autoincrement=False, nullable=True),
        sa.Column('legal_name', sa.String(1000), nullable=True),
        sa.Column('founding_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('state_filing_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['state_filing_id'], ['filing.id']), # not entirely sure this is the right relationship
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('legacy_outputs',
        sa.Column('colin_event_id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('legacy_output_id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('filing_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['filing_id'], ['filing.id'])
    )

def downgrade():
    op.drop_table('shadow_filings')
    op.drop_table('shadow_business')
    op.drop_table('shadow_legacy_outputs')
