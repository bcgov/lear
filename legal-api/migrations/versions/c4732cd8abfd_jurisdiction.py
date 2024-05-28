"""jurisdiction

Revision ID: c4732cd8abfd
Revises: ef8f033d317b
Create Date: 2024-05-24 14:38:45.440604

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c4732cd8abfd'
down_revision = 'ef8f033d317b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('jurisdictions',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('country', sa.String(length=10), nullable=False),
                    sa.Column('region', sa.String(length=10), nullable=True),
                    sa.Column('identifier', sa.String(length=50), nullable=True),
                    sa.Column('legal_name', sa.String(length=1000), nullable=True),
                    sa.Column('tax_id', sa.String(length=15), nullable=True),
                    sa.Column('incorporation_date', sa.DateTime(timezone=True), nullable=True),
                    sa.Column('expro_identifier', sa.String(length=10), nullable=True),
                    sa.Column('expro_legal_name', sa.String(length=1000), nullable=True),
                    sa.Column('business_id', sa.Integer(), nullable=False),
                    sa.Column('filing_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ),
                    sa.ForeignKeyConstraint(['filing_id'], ['filings.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_jurisdictions_business_id'), 'jurisdictions', ['business_id'], unique=False)
    op.create_index(op.f('ix_jurisdictions_filing_id'), 'jurisdictions', ['filing_id'], unique=False)

    op.create_table('jurisdictions_version',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('country', sa.String(length=10), nullable=False),
                    sa.Column('region', sa.String(length=10), nullable=True),
                    sa.Column('identifier', sa.String(length=50), nullable=True),
                    sa.Column('legal_name', sa.String(length=1000), nullable=True),
                    sa.Column('tax_id', sa.String(length=15), nullable=True),
                    sa.Column('incorporation_date', sa.DateTime(timezone=True), nullable=True),
                    sa.Column('expro_identifier', sa.String(length=10), nullable=True),
                    sa.Column('expro_legal_name', sa.String(length=1000), nullable=True),
                    sa.Column('business_id', sa.Integer(), nullable=False),
                    sa.Column('filing_id', sa.Integer(), nullable=False),
                    sa.Column('transaction_id', sa.BigInteger(), autoincrement=False, nullable=False),
                    sa.Column('end_transaction_id', sa.BigInteger(), nullable=True),
                    sa.Column('operation_type', sa.SmallInteger(), nullable=False),
                    sa.ForeignKeyConstraint(['filing_id'], ['filings.id']),
                    sa.ForeignKeyConstraint(['business_id'], ['businesses.id']),
                    sa.PrimaryKeyConstraint('id', 'transaction_id')
                    )
    op.create_index(op.f('ix_jurisdictions_version_end_transaction_id'), 'jurisdictions_version', ['end_transaction_id'], unique=False)
    op.create_index(op.f('ix_jurisdictions_version_business_id'), 'jurisdictions_version', ['business_id'], unique=False)
    op.create_index(op.f('ix_jurisdictions_version_filing_id'), 'jurisdictions_version', ['filing_id'], unique=False)
    op.create_index(op.f('ix_jurisdictions_version_operation_type'), 'jurisdictions_version', ['operation_type'], unique=False)
    op.create_index(op.f('ix_jurisdictions_version_transaction_id'), 'jurisdictions_version', ['transaction_id'], unique=False)

    op.drop_column('businesses', 'foreign_legal_type')
    op.drop_column('businesses', 'foreign_identifier')
    op.drop_column('businesses', 'foreign_incorporation_date')

    op.drop_column('businesses_version', 'foreign_legal_type')
    op.drop_column('businesses_version', 'foreign_identifier')
    op.drop_column('businesses_version', 'foreign_incorporation_date')

    op.add_column('documents', sa.Column('file_name', sa.String(length=1000), nullable=True))
    op.add_column('documents_version', sa.Column('file_name', sa.String(length=1000), nullable=True))


def downgrade():
    op.drop_column('documents_version', 'file_name')
    op.drop_column('documents', 'file_name')

    op.add_column('businesses_version', sa.Column('foreign_incorporation_date', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True))
    op.add_column('businesses_version', sa.Column('foreign_identifier', sa.VARCHAR(length=15), autoincrement=False, nullable=True))
    op.add_column('businesses_version', sa.Column('foreign_legal_type', sa.VARCHAR(length=10), autoincrement=False, nullable=True))

    op.add_column('businesses', sa.Column('foreign_incorporation_date', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True))
    op.add_column('businesses', sa.Column('foreign_identifier', sa.VARCHAR(length=15), autoincrement=False, nullable=True))
    op.add_column('businesses', sa.Column('foreign_legal_type', sa.VARCHAR(length=10), autoincrement=False, nullable=True))

    op.drop_index(op.f('ix_jurisdictions_version_end_transaction_id'), table_name='jurisdictions_version')
    op.drop_index(op.f('ix_jurisdictions_version_business_id'), table_name='jurisdictions_version')
    op.drop_index(op.f('ix_jurisdictions_version_filing_id'), table_name='jurisdictions_version')
    op.drop_index(op.f('ix_jurisdictions_version_operation_type'), table_name='jurisdictions_version')
    op.drop_index(op.f('ix_jurisdictions_version_transaction_id'), table_name='jurisdictions_version')
    op.drop_table('jurisdictions_version')

    op.drop_index(op.f('ix_jurisdictions_business_id'), table_name='jurisdictions')
    op.drop_index(op.f('ix_jurisdictions_filing_id'), table_name='jurisdictions')
    op.drop_table('jurisdictions')
